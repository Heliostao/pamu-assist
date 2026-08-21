"""认证接口：发验证码、邮箱验证码登录、邮箱密码登录、当前用户信息。"""
import asyncio
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.auth import redis_client
from src.auth.email_service import send_vcode_email
from src.auth.security import create_token, get_current_user, hash_password
from src.database.db import get_db
from src.database.models import User
from src.util.config import DEFAULT_PASSWORD, DEFAULT_USERNAME

router = APIRouter(prefix="/auth", tags=["auth"])

EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")


class VcodeRequest(BaseModel):
    email: str = Field(..., description="邮箱地址")


class EmailLoginRequest(BaseModel):
    email: str
    vcode: str = Field(..., min_length=6, max_length=6)


class PasswordLoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=6, max_length=64)


def _validate_email(email: str) -> None:
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")


def _get_or_create_user(db, email: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(email=email, nickname=email.split("@")[0])
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def _user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "nickname": user.nickname,
    }


@router.post("/vcode")
async def send_vcode(req: VcodeRequest):
    """发送登录验证码到指定邮箱（60s 冷却、5 分钟有效）。"""
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


@router.post("/login/email")
async def login_by_email(req: EmailLoginRequest, db=Depends(get_db)):
    """邮箱验证码登录，无账号自动注册。"""
    email = req.email.strip().lower()
    _validate_email(email)

    saved = redis_client.get_code(email)
    if saved is None:
        raise HTTPException(status_code=400, detail="验证码不存在或已过期，请重新获取")
    if saved != req.vcode:
        raise HTTPException(status_code=400, detail="验证码错误")

    redis_client.delete_code(email)
    user = _get_or_create_user(db, email)
    token = create_token(user.id, user.email)
    return {"token": token, "user": _user_payload(user)}


@router.post("/login/password")
async def login_by_password(req: PasswordLoginRequest, db=Depends(get_db)):
    """默认账号密码登录（账号由 .env 的 DEFAULT_USERNAME / DEFAULT_PASSWORD 配置）。"""
    username = req.username.strip()
    if username != DEFAULT_USERNAME or req.password != DEFAULT_PASSWORD:
        # 统一提示，避免暴露账号是否存在
        raise HTTPException(status_code=400, detail="账号或密码错误")

    # 正常情况下 init_db 已建好默认账号，此处兜底确保存在
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        user = User(
            username=username,
            email=f"{username}@local",
            nickname=username,
            password_hash=hash_password(req.password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_token(user.id, user.email)
    return {"token": token, "user": _user_payload(user)}


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    """返回当前登录用户信息。"""
    return _user_payload(user)
