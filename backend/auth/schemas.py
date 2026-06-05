"""
认证模块数据模型（Pydantic Schemas）
- 定义请求和响应的数据结构
- 用于 API 参数验证和序列化
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    """用户注册请求"""
    username: str                          # 用户名
    email: EmailStr                        # 邮箱
    password: str                          # 密码
    full_name: Optional[str] = None        # 姓名
    department: Optional[str] = None       # 部门


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str                          # 用户名
    password: str                          # 密码


class Token(BaseModel):
    """Token 响应"""
    access_token: str                      # 访问令牌
    refresh_token: str                     # 刷新令牌
    token_type: str = "bearer"             # 令牌类型


class TokenRefresh(BaseModel):
    """Token 刷新请求"""
    refresh_token: str                     # 刷新令牌


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int                                # 用户 ID
    username: str                          # 用户名
    email: str                             # 邮箱
    full_name: Optional[str]               # 姓名
    department: Optional[str]              # 部门
    is_active: bool                        # 是否启用
    roles: list[str]                       # 角色列表
    created_at: datetime                   # 创建时间

    class Config:
        from_attributes = True             # 支持从 ORM 对象转换


class RoleCreate(BaseModel):
    """角色创建请求"""
    name: str                              # 角色名
    description: Optional[str] = None      # 描述
    permissions: Optional[str] = None      # 权限（JSON 字符串）


class UserRoleAssign(BaseModel):
    """角色分配请求"""
    user_id: int                           # 用户 ID
    role_name: str                         # 角色名
