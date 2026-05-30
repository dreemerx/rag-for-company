from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# 用户创建
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    department: Optional[str] = None


# 用户登录
class UserLogin(BaseModel):
    username: str
    password: str


# Token 响应
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# Token 刷新请求
class TokenRefresh(BaseModel):
    refresh_token: str


# 用户响应
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    department: Optional[str]
    is_active: bool
    roles: list[str]
    created_at: datetime

    class Config:
        from_attributes = True


# 角色创建
class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: Optional[str] = None


# 角色分配
class UserRoleAssign(BaseModel):
    user_id: int
    role_name: str
