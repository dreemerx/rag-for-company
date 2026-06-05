"""RBAC 权限模型测试"""
import pytest
import json
from backend.auth.models import Role, User


def test_role_permission_list_json():
    """测试 JSON 格式权限解析"""
    role = Role(
        name="test",
        description="测试角色",
        permissions=json.dumps(["read", "write", "delete"]),
    )
    assert role.permission_list == ["read", "write", "delete"]


def test_role_permission_list_csv():
    """测试逗号分隔格式权限解析（向后兼容）"""
    role = Role(
        name="test",
        description="测试角色",
        permissions="read,write,delete",
    )
    assert role.permission_list == ["read", "write", "delete"]


def test_role_permission_list_empty():
    """测试空权限"""
    role = Role(name="test", description="测试角色", permissions=None)
    assert role.permission_list == []

    role2 = Role(name="test", description="测试角色", permissions="")
    assert role2.permission_list == []


def test_user_has_role():
    """测试用户角色检查"""
    role = Role(name="admin", description="管理员")
    user = User(
        username="test",
        email="test@test.com",
        hashed_password="xxx",
        roles=[role],
    )
    assert user.has_role("admin")
    assert not user.has_role("user")


def test_user_has_permission():
    """测试用户权限检查（精确匹配）"""
    role = Role(
        name="user",
        description="普通用户",
        permissions=json.dumps(["knowledge_base", "database_query"]),
    )
    user = User(
        username="test",
        email="test@test.com",
        hashed_password="xxx",
        roles=[role],
    )
    assert user.has_permission("knowledge_base")
    assert user.has_permission("database_query")
    assert not user.has_permission("admin_panel")


def test_user_permission_no_substring_match():
    """测试权限不会子串匹配"""
    role = Role(
        name="user",
        description="普通用户",
        permissions=json.dumps(["read"]),
    )
    user = User(
        username="test",
        email="test@test.com",
        hashed_password="xxx",
        roles=[role],
    )
    assert user.has_permission("read")
    # 不应该匹配到 "bread" 或 "reading"
    assert not user.has_permission("bread")
    assert not user.has_permission("reading")


def test_user_role_names():
    """测试获取用户角色名列表"""
    roles = [
        Role(name="user", description="普通用户"),
        Role(name="editor", description="编辑"),
    ]
    user = User(
        username="test",
        email="test@test.com",
        hashed_password="xxx",
        roles=roles,
    )
    assert user.role_names == ["user", "editor"]
