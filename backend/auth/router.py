from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .models import User, Role
from .schemas import UserCreate, UserLogin, Token, TokenRefresh, UserResponse, UserRoleAssign
from .jwt_handler import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from .rbac import get_current_user, require_role, get_db

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """用户注册"""
    try:
        return await _register_user(user_data, db)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


async def _register_user(user_data: UserCreate, db: AsyncSession):
    """内部注册逻辑"""
    # 检查用户名是否已存在
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )

    # 检查邮箱是否已存在
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册"
        )

    # 获取默认用户角色
    result = await db.execute(select(Role).where(Role.name == "user"))
    default_role = result.scalar_one_or_none()

    if not default_role:
        # 创建默认角色
        default_role = Role(name="user", description="普通用户", permissions="knowledge_base,database_query,ticket,email,approval_query")
        db.add(default_role)
        await db.flush()

    # 创建用户
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        department=user_data.department,
        roles=[default_role],
    )
    db.add(user)
    await db.flush()
    await db.refresh(user, ["roles"])

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        department=user.department,
        is_active=user.is_active,
        roles=[role.name for role in user.roles],
        created_at=user.created_at,
    )


@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    result = await db.execute(
        select(User)
        .where(User.username == user_data.username)
        .options(selectinload(User.roles))
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用"
        )

    return Token(
        access_token=create_access_token(data={"sub": user.username}),
        refresh_token=create_refresh_token(data={"sub": user.username}),
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(token_data: TokenRefresh, db: AsyncSession = Depends(get_db)):
    """刷新令牌"""
    payload = verify_token(token_data.refresh_token, token_type="refresh")
    username = payload.get("sub")

    result = await db.execute(
        select(User)
        .where(User.username == username)
        .options(selectinload(User.roles))
    )
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌"
        )

    return Token(
        access_token=create_access_token(data={"sub": user.username}),
        refresh_token=create_refresh_token(data={"sub": user.username}),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        department=current_user.department,
        is_active=current_user.is_active,
        roles=[role.name for role in current_user.roles],
        created_at=current_user.created_at,
    )


@router.post("/assign-role", response_model=dict)
async def assign_role(
    role_data: UserRoleAssign,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """分配角色（仅管理员）"""
    # 查找用户
    result = await db.execute(
        select(User).where(User.id == role_data.user_id).options(selectinload(User.roles))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 查找角色
    result = await db.execute(select(Role).where(Role.name == role_data.role_name))
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    # 分配角色
    if role not in user.roles:
        user.roles.append(role)
        await db.flush()

    return {"message": f"已将角色 {role.name} 分配给用户 {user.username}"}
