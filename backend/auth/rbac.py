import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .jwt_handler import verify_token
from .models import User

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_db():
    """获取数据库会话（统一入口）"""
    from backend.database import get_session_factory
    factory = get_session_factory()
    if factory is None:
        raise HTTPException(status_code=500, detail="数据库未初始化")
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.exception(f"数据库会话异常: {e}")
            raise
        finally:
            await session.close()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """获取当前认证用户"""
    payload = verify_token(credentials.credentials, token_type="access")
    username = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据"
        )

    result = await db.execute(
        select(User)
        .where(User.username == username)
        .options(selectinload(User.roles))
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    return user


def require_role(*role_names: str):
    """角色权限装饰器"""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if not any(current_user.has_role(role) for role in role_names):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要以下角色之一: {', '.join(role_names)}"
            )
        return current_user
    return role_checker


def require_permission(*permission_names: str):
    """细粒度权限装饰器"""
    async def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        if not any(current_user.has_permission(perm) for perm in permission_names):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"缺少权限: {', '.join(permission_names)}"
            )
        return current_user
    return permission_checker
