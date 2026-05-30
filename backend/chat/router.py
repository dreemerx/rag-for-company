from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from typing import Optional
import json

from backend.auth.models import User
from backend.auth.rbac import get_current_user
from backend.agent.core import get_agent
from backend.chat.session_manager import get_session_manager
from backend.chat.rate_limiter import get_rate_limiter

chat_router = APIRouter(prefix="/chat", tags=["对话"])


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    remaining_quota: dict


@chat_router.post("/send", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """发送消息（HTTP）"""
    try:
        # 检查限流
        rate_limiter = get_rate_limiter()
        rate_limiter.check_rate_limit(str(current_user.id))

        # 获取或创建会话
        session_manager = get_session_manager()
        if request.session_id:
            session = session_manager.get_session(request.session_id)
            if not session or session.user_id != str(current_user.id):
                raise HTTPException(status_code=404, detail="会话不存在")
            session_id = request.session_id
        else:
            session_id = session_manager.create_session(str(current_user.id))

        # 调用 Agent
        agent = get_agent()
        reply = await agent.chat(
            user_id=str(current_user.id),
            user_name=current_user.full_name or current_user.username,
            department=current_user.department or "",
            role=current_user.role_names[0] if current_user.role_names else "user",
            message=request.message,
        )

        # 更新会话和限流记录
        tokens_used = len(reply) // 2  # 粗略估算
        session_manager.update_session(session_id, tokens_used)
        rate_limiter.record_request(str(current_user.id), tokens_used)

        return ChatResponse(
            reply=reply,
            session_id=session_id,
            remaining_quota=rate_limiter.get_remaining_quota(str(current_user.id)),
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ChatResponse(
            reply=f"抱歉，处理您的请求时出现问题: {str(e)}。请稍后再试。",
            session_id=request.session_id or "",
            remaining_quota=get_rate_limiter().get_remaining_quota(str(current_user.id)),
        )


@chat_router.websocket("/ws/{token}")
async def websocket_chat(websocket: WebSocket, token: str):
    """WebSocket 实时对话"""
    await websocket.accept()

    # 验证 token
    try:
        from backend.auth.jwt_handler import verify_token
        payload = verify_token(token, token_type="access")
        username = payload.get("sub")
    except Exception:
        await websocket.close(code=4001, reason="认证失败")
        return

    # 获取用户信息
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from backend.database import _async_session_factory
    from backend.auth.models import User

    if _async_session_factory is None:
        await websocket.close(code=4001, reason="数据库未初始化")
        return

    async with _async_session_factory() as db:
        result = await db.execute(
            select(User).where(User.username == username).options(selectinload(User.roles))
        )
        user = result.scalar_one_or_none()

    if not user:
        await websocket.close(code=4001, reason="用户不存在")
        return

    session_manager = get_session_manager()
    session_id = session_manager.create_session(str(user.id))
    rate_limiter = get_rate_limiter()

    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message_data = json.loads(data)
            message = message_data.get("message", "")

            if not message:
                continue

            # 检查限流
            try:
                rate_limiter.check_rate_limit(str(user.id))
            except HTTPException:
                await websocket.send_json({
                    "error": "请求过于频繁，请稍后再试",
                    "type": "rate_limit"
                })
                continue

            # 调用 Agent
            agent = get_agent()
            reply = await agent.chat(
                user_id=str(user.id),
                user_name=user.full_name or user.username,
                department=user.department or "",
                role=user.role_names[0] if user.role_names else "user",
                message=message,
            )

            # 更新会话
            tokens_used = len(reply) // 2
            session_manager.update_session(session_id, tokens_used)
            rate_limiter.record_request(str(user.id), tokens_used)

            # 发送回复
            await websocket.send_json({
                "reply": reply,
                "session_id": session_id,
                "type": "message"
            })

    except WebSocketDisconnect:
        session_manager.delete_session(session_id)


@chat_router.get("/sessions")
async def get_sessions(current_user: User = Depends(get_current_user)):
    """获取用户的会话列表"""
    session_manager = get_session_manager()
    sessions = session_manager.get_user_sessions(str(current_user.id))
    return [
        {
            "session_id": s.session_id,
            "created_at": s.created_at.isoformat(),
            "last_active": s.last_active.isoformat(),
            "message_count": s.message_count,
        }
        for s in sessions
    ]


@chat_router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """删除会话"""
    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)

    if not session or session.user_id != str(current_user.id):
        raise HTTPException(status_code=404, detail="会话不存在")

    session_manager.delete_session(session_id)
    agent = get_agent()
    agent.clear_session(str(current_user.id))

    return {"message": "会话已删除"}
