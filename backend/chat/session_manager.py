from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class Session:
    """会话数据"""
    session_id: str
    user_id: str
    created_at: datetime
    last_active: datetime
    message_count: int = 0
    total_tokens: int = 0


class SessionManager:
    """
    会话管理器
    管理多用户会话，支持会话隔离
    """

    def __init__(self):
        self._sessions: Dict[str, Session] = {}

    def create_session(self, user_id: str) -> str:
        """创建新会话"""
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()

        session = Session(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            last_active=now,
        )

        self._sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return self._sessions.get(session_id)

    def get_user_sessions(self, user_id: str) -> list[Session]:
        """获取用户的所有会话"""
        return [
            session for session in self._sessions.values()
            if session.user_id == user_id
        ]

    def update_session(self, session_id: str, tokens_used: int = 0) -> None:
        """更新会话活动"""
        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.last_active = datetime.utcnow()
            session.message_count += 1
            session.total_tokens += tokens_used

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def cleanup_expired_sessions(self, max_idle_minutes: int = 30) -> int:
        """清理过期会话"""
        now = datetime.utcnow()
        expired = []

        for session_id, session in self._sessions.items():
            idle_time = (now - session.last_active).total_seconds() / 60
            if idle_time > max_idle_minutes:
                expired.append(session_id)

        for session_id in expired:
            del self._sessions[session_id]

        return len(expired)

    def get_session_count(self) -> int:
        """获取活跃会话数量"""
        return len(self._sessions)


# 单例
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """获取会话管理器单例"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
