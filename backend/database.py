from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from backend.config.settings import get_settings
from backend.auth.models import Base
from backend.chat.models import ChatSession, ChatMessage  # noqa: F401 - 确保表被创建

# 全局引擎
_engine = None
_async_session_factory = None


async def init_db():
    """初始化数据库"""
    global _engine, _async_session_factory

    settings = get_settings()
    _engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        future=True,
    )

    _async_session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # 创建表
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_session_factory():
    """获取会话工厂（供 get_db 使用）"""
    return _async_session_factory


async def close_db():
    """关闭数据库连接"""
    global _engine
    if _engine:
        await _engine.dispose()
