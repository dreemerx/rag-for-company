"""
内存会话管理模块
- 管理运行时会话状态（与数据库持久化的 ChatSession 不同）
- 支持会话创建、查询、更新、删除
- 支持过期会话自动清理
"""
from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class Session:
    """
    会话数据类

    Attributes:
        session_id: 会话 ID
        user_id: 用户 ID
        created_at: 创建时间
        last_active: 最后活跃时间
        message_count: 消息计数
        total_tokens: Token 总消耗
    """
    session_id: str
    user_id: str
    created_at: datetime
    last_active: datetime
    message_count: int = 0
    total_tokens: int = 0


class SessionManager:
    """
    内存会话管理器
    - 使用内存字典存储会话状态
    - 支持多用户会话隔离
    - 支持过期会话自动清理
    """

    def __init__(self):
        """初始化会话管理器"""
        self._sessions: Dict[str, Session] = {}

    def create_session(self, user_id: str) -> str:
        """
        创建新会话

        Args:
            user_id: 用户 ID

        Returns:
            新会话 ID
        """
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
        """
        获取会话

        Args:
            session_id: 会话 ID

        Returns:
            会话数据，不存在返回 None
        """
        return self._sessions.get(session_id)

    def get_user_sessions(self, user_id: str) -> list[Session]:
        """
        获取用户的所有会话

        Args:
            user_id: 用户 ID

        Returns:
            会话列表
        """
        return [
            session for session in self._sessions.values()
            if session.user_id == user_id
        ]

    def update_session(self, session_id: str, tokens_used: int = 0) -> None:
        """
        更新会话活动（刷新活跃时间、累加消息数和 Token 消耗）

        Args:
            session_id: 会话 ID
            tokens_used: 本次消耗的 Token 数
        """
        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.last_active = datetime.utcnow()
            session.message_count += 1
            session.total_tokens += tokens_used

    def delete_session(self, session_id: str) -> bool:
        """
        删除会话

        Args:
            session_id: 会话 ID

        Returns:
            是否删除成功
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def cleanup_expired_sessions(self, max_idle_minutes: int = 30) -> int:
        """
        清理过期会话

        Args:
            max_idle_minutes: 最大空闲时间（分钟）

        Returns:
            清理的会话数量
        """
        now = datetime.utcnow()
        expired = []

        # 找出所有超过空闲时间的会话
        for session_id, session in self._sessions.items():
            idle_time = (now - session.last_active).total_seconds() / 60
            if idle_time > max_idle_minutes:
                expired.append(session_id)

        # 删除过期会话
        for session_id in expired:
            del self._sessions[session_id]

        return len(expired)

    def get_session_count(self) -> int:
        """
        获取活跃会话数量

        Returns:
            会话数量
        """
        return len(self._sessions)


# 单例
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """
    获取会话管理器单例

    Returns:
        SessionManager 实例
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
