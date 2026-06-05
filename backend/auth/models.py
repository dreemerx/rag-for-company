import json
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Table
from sqlalchemy.orm import relationship, DeclarativeBase
from datetime import datetime


class Base(DeclarativeBase):
    pass


# 用户-角色关联表
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
)


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # admin, manager, user
    description = Column(String(200))
    permissions = Column(String(500))  # JSON array of permissions

    users = relationship("User", secondary=user_roles, back_populates="roles")

    @property
    def permission_list(self) -> list[str]:
        """解析权限列表"""
        if not self.permissions:
            return []
        try:
            return json.loads(self.permissions)
        except (json.JSONDecodeError, TypeError):
            # 兼容旧的逗号分隔格式
            return [p.strip() for p in self.permissions.split(",") if p.strip()]


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    full_name = Column(String(100))
    department = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    roles = relationship("Role", secondary=user_roles, back_populates="users")

    @property
    def role_names(self) -> list[str]:
        return [role.name for role in self.roles]

    def has_role(self, role_name: str) -> bool:
        return role_name in self.role_names

    def has_permission(self, permission: str) -> bool:
        """精确匹配权限（使用 JSON 数组）"""
        for role in self.roles:
            if permission in role.permission_list:
                return True
        return False
