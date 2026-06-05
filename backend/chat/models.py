"""
对话模块数据模型
- ChatSession：对话会话表
- ChatMessage：对话消息表
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.auth.models import Base


class ChatSession(Base):
    """对话会话表"""
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)                    # 会话 ID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # 关联用户
    title = Column(String(200), default="新对话")                          # 会话标题
    summary = Column(Text, default="")                                    # 对话摘要（旧消息压缩）
    created_at = Column(DateTime, default=datetime.utcnow)                # 创建时间
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 更新时间

    # 关联消息，级联删除
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    """对话消息表"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)                    # 消息 ID
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)  # 关联会话
    role = Column(String(20), nullable=False)                             # 角色（user/assistant）
    content = Column(Text, nullable=False)                                # 消息内容
    tokens_used = Column(Integer, default=0)                              # Token 消耗量
    created_at = Column(DateTime, default=datetime.utcnow)                # 创建时间

    # 关联回话
    session = relationship("ChatSession", back_populates="messages")
