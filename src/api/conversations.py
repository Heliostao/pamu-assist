"""历史对话接口：会话列表、新建、删除、消息查询。"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.auth.security import get_current_user
from src.database.db import get_db
from src.database.models import Conversation, Message, User

router = APIRouter(prefix="/conversations", tags=["conversations"])


class CreateConversationRequest(BaseModel):
    title: str = Field(default="新对话", max_length=255)


class SaveMessageRequest(BaseModel):
    conversation_id: int
    role: str
    content: str


def _get_owned_conversation(db, conv_id: int, user: User) -> Conversation:
    conv = db.get(Conversation, conv_id)
    if conv is None or conv.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    return conv


@router.get("")
async def list_conversations(
    user: User = Depends(get_current_user), db=Depends(get_db)
):
    """当前用户的会话列表（按更新时间倒序）。"""
    convs = (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return [
        {
            "id": c.id,
            "title": c.title,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in convs
    ]


@router.post("")
async def create_conversation(
    req: CreateConversationRequest,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    conv = Conversation(user_id=user.id, title=req.title.strip() or "新对话")
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return {"id": conv.id, "title": conv.title}


@router.delete("/{conv_id}")
async def delete_conversation(
    conv_id: int,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    conv = _get_owned_conversation(db, conv_id, user)
    db.delete(conv)
    db.commit()
    return {"message": "已删除"}


@router.get("/{conv_id}/messages")
async def list_messages(
    conv_id: int,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """某会话的消息列表（按 id 升序）。"""
    _get_owned_conversation(db, conv_id, user)
    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conv_id)
        .order_by(Message.id.asc())
        .all()
    )
    return [{"id": m.id, "role": m.role, "content": m.content} for m in msgs]


def save_chat_messages(db, conversation_id: int, user_id: int, user_text: str, assistant_text: str) -> None:
    """保存一轮问答消息并更新会话时间（供 /chat 调用）。"""
    conv = db.get(Conversation, conversation_id)
    if conv is None or conv.user_id != user_id:
        raise HTTPException(status_code=404, detail="会话不存在")

    db.add(Message(conversation_id=conversation_id, role="user", content=user_text))
    db.add(Message(conversation_id=conversation_id, role="assistant", content=assistant_text))
    if conv.title == "新对话":
        conv.title = user_text[:30]
    conv.updated_at = datetime.now(timezone.utc)
    db.commit()
