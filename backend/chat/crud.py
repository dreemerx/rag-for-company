from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import ChatSession, ChatMessage


async def create_session(db: AsyncSession, user_id: int, title: str = "新对话") -> ChatSession:
    """创建新对话"""
    session = ChatSession(user_id=user_id, title=title)
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


async def get_user_sessions(db: AsyncSession, user_id: int) -> List[ChatSession]:
    """获取用户的所有对话（按更新时间倒序）"""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(desc(ChatSession.updated_at))
    )
    return list(result.scalars().all())


async def get_session(db: AsyncSession, session_id: int, user_id: int) -> Optional[ChatSession]:
    """获取单个对话（校验用户）"""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def delete_session(db: AsyncSession, session_id: int, user_id: int) -> bool:
    """删除对话"""
    session = await get_session(db, session_id, user_id)
    if not session:
        return False
    await db.delete(session)
    return True


async def update_session_title(db: AsyncSession, session_id: int, user_id: int, title: str) -> Optional[ChatSession]:
    """更新对话标题"""
    session = await get_session(db, session_id, user_id)
    if not session:
        return None
    session.title = title
    await db.flush()
    return session


async def add_message(db: AsyncSession, session_id: int, role: str, content: str, tokens_used: int = 0) -> ChatMessage:
    """添加消息"""
    msg = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        tokens_used=tokens_used,
    )
    db.add(msg)
    await db.flush()
    return msg


async def get_session_messages(db: AsyncSession, session_id: int) -> List[ChatMessage]:
    """获取对话的所有消息"""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    return list(result.scalars().all())
