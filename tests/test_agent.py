import pytest
from backend.agent.core import AgentCore
from backend.tools.registry import get_tool_registry


def test_agent_initialization():
    """测试 Agent 初始化"""
    agent = AgentCore()
    assert agent.registry is not None
    assert agent.client is not None
    assert agent.model is not None


def test_agent_tools_for_user():
    """测试不同角色的工具权限"""
    registry = get_tool_registry()

    user_tools = registry.get_tools_for_role("user")
    manager_tools = registry.get_tools_for_role("manager")
    admin_tools = registry.get_tools_for_role("admin")

    # 管理员应该有最多的工具
    assert len(admin_tools) >= len(manager_tools)
    assert len(manager_tools) >= len(user_tools)


def test_tool_schema_generation():
    """测试工具 schema 生成"""
    agent = AgentCore()
    schema = agent._get_tools_schema("user")
    assert isinstance(schema, list)
    # 每个工具应该有正确的结构
    for tool in schema:
        assert "type" in tool
        assert tool["type"] == "function"
        assert "function" in tool
        assert "name" in tool["function"]
        assert "description" in tool["function"]
