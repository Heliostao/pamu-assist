"""认证接口：发验证码、账号注册（绑定邮箱）、密码登录、邮箱验证码登录、当前用户信息。"""
import asyncio
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, or_

from src.auth import redis_client
from src.auth.email_service import send_vcode_email
from src.auth.security import create_token, get_current_user, hash_password, verify_password
from src.database.db import get_db
from src.database.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{2,32}$")


class VcodeRequest(BaseModel):
    email: str = Field(..., description="邮箱地址")


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=32, description="账号")
    password: str = Field(..., min_length=6, max_length=64, description="密码")
    email: str = Field(..., description="邮箱")
    vcode: str = Field(..., min_length=6, max_length=6, description="邮箱验证码")
    nickname: str | None = Field(None, max_length=32, description="用户名/昵称，用于展示，留空则默认与账号一致")


class EmailLoginRequest(BaseModel):
    email: str
    vcode: str = Field(..., min_length=6, max_length=6)


class PasswordLoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64, description="账号或邮箱")
    password: str = Field(..., min_length=6, max_length=64)


def _validate_email(email: str) -> None:
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")


def _validate_username(username: str) -> None:
    if not USERNAME_RE.match(username):
        raise HTTPException(status_code=400, detail="账号需为 2-32 位字母、数字或下划线")


def _user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "nickname": user.nickname,
    }


@router.post("/vcode")
async def send_vcode(req: VcodeRequest):
    """发送验证码到指定邮箱（60s 冷却、5 分钟有效），用于注册时绑定邮箱。"""
    email = req.email.strip().lower()
    _validate_email(email)

    if not redis_client.can_resend(email):
        raise HTTPException(status_code=429, detail="发送过于频繁，请 60 秒后再试")

    code = redis_client.gen_code()
    redis_client.save_code(email, code)
    try:
        await asyncio.to_thread(send_vcode_email, email, code)
    except Exception:
        redis_client.delete_code(email)
        raise HTTPException(status_code=502, detail="邮件发送失败，请稍后重试")

    return {"message": "验证码已发送，请注意查收（5 分钟内有效）"}


@router.post("/register")
async def register(req: RegisterRequest, db=Depends(get_db)):
    """账号注册：账号唯一 + 邮箱验证码绑定。注册成功后账号与邮箱绑定，可用账号或邮箱 + 密码登录。"""
    username = req.username.strip()
    email = req.email.strip().lower()
    _validate_username(username)
    _validate_email(email)

    # 账号唯一性（不区分大小写，防止 "Tom" / "tom" 重复）
    if (
        db.query(User)
        .filter(func.lower(User.username) == username.lower())
        .first()
        is not None
    ):
        raise HTTPException(status_code=409, detail="账号已存在")

    # 邮箱唯一性：已绑定账号的邮箱不可重复注册
    exist = db.query(User).filter(User.email == email).first()
    if exist is not None and exist.username is not None:
        raise HTTPException(status_code=409, detail="该邮箱已绑定账号")

    # 验证码校验（注册必须经过邮箱验证，防止恶意批量注册）
    saved = redis_client.get_code(email)
    if saved is None:
        raise HTTPException(status_code=400, detail="验证码不存在或已过期，请重新获取")
    if saved != req.vcode:
        raise HTTPException(status_code=400, detail="验证码错误")
    redis_client.delete_code(email)

    # 用户名（展示用）：可选，留空则默认与账号一致
    nickname = (req.nickname or "").strip()
    if len(nickname) > 32:
        raise HTTPException(status_code=400, detail="用户名不能超过 32 个字符")
    nickname = nickname or username

    password_hash = hash_password(req.password)
    if exist is not None:
        # 补全历史幽灵账号：此前邮箱验证码登录自动创建的未绑定账号，注册时补上用户名与密码
        exist.username = username
        exist.password_hash = password_hash
        exist.nickname = nickname
        db.commit()
        db.refresh(exist)
        user = exist
    else:
        user = User(
            username=username,
            email=email,
            nickname=nickname,
            password_hash=password_hash,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_token(user.id, user.email)
    return {"token": token, "user": _user_payload(user)}


@router.post("/login/password")
async def login_by_password(req: PasswordLoginRequest, db=Depends(get_db)):
    """账号或邮箱 + 密码登录（密码为 bcrypt 哈希校验）。"""
    account = req.username.strip().lower()

    user = (
        db.query(User)
        .filter(
            or_(
                func.lower(User.username) == account,
                func.lower(User.email) == account,
            )
        )
        .first()
    )
    # 统一提示
    if user is None or user.password_hash is None:
        raise HTTPException(status_code=400, detail="账号或密码错误")
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=400, detail="账号或密码错误")

    token = create_token(user.id, user.email)
    return {"token": token, "user": _user_payload(user)}


@router.post("/login/email")
async def login_by_email(req: EmailLoginRequest, db=Depends(get_db)):
    """邮箱验证码登录：仅限已绑定账号的邮箱，未注册邮箱请先注册。"""
    email = req.email.strip().lower()
    _validate_email(email)

    user = db.query(User).filter(User.email == email).first()
    if user is None or user.username is None:
        raise HTTPException(status_code=400, detail="该邮箱尚未注册，请先注册账号")

    saved = redis_client.get_code(email)
    if saved is None:
        raise HTTPException(status_code=400, detail="验证码不存在或已过期，请重新获取")
    if saved != req.vcode:
        raise HTTPException(status_code=400, detail="验证码错误")

    redis_client.delete_code(email)
    token = create_token(user.id, user.email)
    return {"token": token, "user": _user_payload(user)}


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    """返回当前登录用户信息。"""
    return _user_payload(user)
