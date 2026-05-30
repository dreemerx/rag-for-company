import pytest
from backend.agent.core import AgentCore
from backend.tools.registry import get_tool_registry


def test_agent_initialization():
    agent = AgentCore()
    assert agent.registry is not None
    assert agent.llm is not None


def test_agent_tools_for_user():
    agent = AgentCore()
    registry = get_tool_registry()

    user_tools = registry.get_tools_for_role("user")
    manager_tools = registry.get_tools_for_role("manager")

    assert len(manager_tools) > len(user_tools)
