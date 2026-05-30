import pytest
from backend.tools.registry import get_tool_registry
from backend.tools.knowledge_base import KnowledgeBaseTool
from backend.tools.database_query import DatabaseQueryTool


def test_tool_registry():
    registry = get_tool_registry()
    tools = registry.get_all_tools()
    assert len(tools) >= 7  # 至少7个工具


def test_user_role_tools():
    registry = get_tool_registry()
    user_tools = registry.get_tools_for_role("user")
    tool_names = [t.name for t in user_tools]

    assert "knowledge_base_search" in tool_names
    assert "database_query" in tool_names
    assert "team_overview" not in tool_names  # 管理层工具


def test_manager_role_tools():
    registry = get_tool_registry()
    manager_tools = registry.get_tools_for_role("manager")
    tool_names = [t.name for t in manager_tools]

    assert "knowledge_base_search" in tool_names
    assert "team_overview" in tool_names
    assert "approval_process" in tool_names


@pytest.mark.asyncio
async def test_database_query_tool():
    tool = DatabaseQueryTool()
    result = await tool.run(query_type="sales")
    assert result.success
    assert "销售" in str(result.data)


@pytest.mark.asyncio
async def test_knowledge_base_empty_query():
    tool = KnowledgeBaseTool()
    result = await tool.run(query="")
    assert not result.success
    assert "关键词" in result.error
