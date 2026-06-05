"""
JWT 令牌处理模块
- 密码哈希与验证（bcrypt）
- 访问令牌和刷新令牌的创建与验证
- 双令牌机制：Access Token（短期）+ Refresh Token（长期）
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from backend.config.settings import get_settings

# 密码加密上下文（使用 bcrypt 算法）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码与哈希密码是否匹配

    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码

    Returns:
        是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    生成密码哈希

    Args:
        password: 明文密码

    Returns:
        哈希后的密码
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建访问令牌

    Args:
        data: 令牌载荷数据（通常包含 {"sub": username}）
        expires_delta: 过期时间增量（默认使用配置值）

    Returns:
        JWT 访问令牌字符串
    """
    settings = get_settings()
    to_encode = data.copy()
    # 设置过期时间
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """
    创建刷新令牌

    Args:
        data: 令牌载荷数据（通常包含 {"sub": username}）

    Returns:
        JWT 刷新令牌字符串
    """
    settings = get_settings()
    to_encode = data.copy()
    # 刷新令牌使用较长的过期时间
    expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str, token_type: str = "access") -> dict:
    """
    验证并解码令牌

    Args:
        token: JWT 令牌字符串
        token_type: 期望的令牌类型（access/refresh）

    Returns:
        解码后的载荷数据

    Raises:
        HTTPException: 令牌无效或过期时抛出 401 错误
    """
    settings = get_settings()
    try:
        # 解码并验证令牌
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        # 检查令牌类型是否匹配
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌类型"
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或已过期的令牌"
        )
