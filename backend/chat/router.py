from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List
import json
import logging

from backend.auth.models import User
from backend.auth.rbac import get_current_user, get_db
from backend.database import get_session_factory
from backend.agent.core import get_agent
from backend.chat.rate_limiter import get_rate_limiter
from backend.chat import crud
from backend.chat.memory import get_memory_manager
from backend.utils import audit_log
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

chat_router = APIRouter(prefix="/chat", tags=["对话"])


# ==================== Schemas ====================

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    session_id: Optional[int] = None


class ChatResponse(BaseModel):
    reply: str
    session_id: int
    remaining_quota: dict


class SessionResponse(BaseModel):
    id: int
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: str

    class Config:
        from_attributes = True


class SessionCreate(BaseModel):
    title: str = "新对话"


class SessionUpdate(BaseModel):
    title: str


# ==================== 工具函数 ====================

def _estimate_tokens(text: str) -> int:
    """
    估算 token 数量
    - 中文：约 1.5 字/token
    - 英文：约 4 字符/token
    - 混合文本：取加权平均
    """
    if not text:
        return 0
    # 简单启发式：中文字符占比
    chinese_chars = sum(1 for c in text if '一' <= c <= '鿿')
    total_chars = len(text)
    if total_chars == 0:
        return 0
    chinese_ratio = chinese_chars / total_chars
    # 中文约 1.5 字/token，英文约 4 字符/token
    avg_chars_per_token = 1.5 * chinese_ratio + 4 * (1 - chinese_ratio)
    return max(1, int(total_chars / avg_chars_per_token))


# ==================== 对话管理 ====================

@chat_router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取对话列表"""
    sessions = await crud.get_user_sessions(db, current_user.id)
    result = []
    for s in sessions:
        msgs = await crud.get_session_messages(db, s.id)
        result.append(SessionResponse(
            id=s.id,
            title=s.title,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
            message_count=len(msgs),
        ))
    return result


@chat_router.post("/sessions", response_model=SessionResponse)
async def create_session(
    body: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """新建对话"""
    session = await crud.create_session(db, current_user.id, body.title)
    return SessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
    )


@chat_router.patch("/sessions/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: int,
    body: SessionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新对话标题"""
    session = await crud.update_session_title(db, session_id, current_user.id, body.title)
    if not session:
        raise HTTPException(status_code=404, detail="对话不存在")
    return SessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
    )


@chat_router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除对话"""
    ok = await crud.delete_session(db, session_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="对话不存在")
    return {"message": "已删除"}


@chat_router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取对话消息历史"""
    session = await crud.get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="对话不存在")
    messages = await crud.get_session_messages(db, session_id)
    return [MessageResponse(
        id=m.id,
        role=m.role,
        content=m.content,
        created_at=m.created_at.isoformat(),
    ) for m in messages]


# ==================== 发送消息（流式） ====================

@chat_router.post("/stream")
async def stream_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SSE 流式输出对话"""
    rate_limiter = get_rate_limiter()
    rate_limiter.check_rate_limit(str(current_user.id))

    logger.info(f"对话请求 user={current_user.id} session={request.session_id}")
    audit_log("chat_message", user_id=current_user.id, username=current_user.username, session_id=request.session_id, message_length=len(request.message))

    # 获取或创建对话
    if request.session_id:
        session = await crud.get_session(db, request.session_id, current_user.id)
        if not session:
            raise HTTPException(status_code=404, detail="对话不存在")
        session_id = session.id
        is_new_session = False
    else:
        session = await crud.create_session(db, current_user.id, "新对话")
        session_id = session.id
        is_new_session = True

    # 保存用户消息
    await crud.add_message(db, session_id, "user", request.message)
    await db.commit()

    # 加载历史消息（滑动窗口 + 摘要压缩）
    memory = get_memory_manager()
    history = await memory.build_context(db, session_id, request.message)

    # 保存用户信息的副本（避免在生成器中依赖数据库会话）
    user_id = str(current_user.id)
    user_name = current_user.full_name or current_user.username
    user_department = current_user.department or ""
    user_role = current_user.role_names[0] if current_user.role_names else "user"

    async def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"

            agent = get_agent()
            full_reply = ""

            async for chunk in agent.chat_stream(
                user_id=user_id,
                session_id=session_id,
                user_name=user_name,
                department=user_department,
                role=user_role,
                message=request.message,
                history=history,
            ):
                full_reply += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            # 保存 AI 回复（使用新的数据库会话）
            tokens_used = _estimate_tokens(full_reply)
            new_title = None
            async with get_session_factory()() as db_session:
                await crud.add_message(db_session, session_id, "assistant", full_reply, tokens_used)

                # 新对话自动生成标题
                if is_new_session:
                    try:
                        new_title = await _generate_title(request.message, full_reply)
                        await crud.update_session_title(db_session, session_id, int(user_id), new_title)
                    except Exception as e:
                        logger.exception(f"标题生成失败 session={session_id}")
                        new_title = request.message[:20] + ("..." if len(request.message) > 20 else "")
                        await crud.update_session_title(db_session, session_id, int(user_id), new_title)

                await db_session.commit()

            rate_limiter.record_request(user_id, tokens_used)
            yield f"data: {json.dumps({'type': 'done', 'title': new_title, 'remaining_quota': rate_limiter.get_remaining_quota(user_id)})}\n\n"

        except Exception as e:
            logger.exception(f"SSE 流异常 user={user_id} session={session_id}")
            yield f"data: {json.dumps({'type': 'error', 'message': '服务器内部错误'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _generate_title(user_msg: str, ai_reply: str) -> str:
    """根据对话内容生成标题（不依赖 LLM，直接截取关键词）"""
    # 简单策略：取用户消息的核心内容作为标题
    title = user_msg.strip()

    # 去掉常见的提问前缀
    for prefix in ["帮我", "请", "我想", "你能", "怎么", "如何", "什么是", "查一下"]:
        if title.startswith(prefix):
            title = title[len(prefix):]

    # 去掉标点
    for char in ["？", "?", "！", "!", "。", ".", "，", ","]:
        title = title.replace(char, "")

    title = title.strip()

    # 限制长度
    if len(title) > 15:
        title = title[:15] + "..."

    return title if title else "新对话"
