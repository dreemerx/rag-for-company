import threading
from typing import Dict, List, Optional
from .base import BaseTool


class ToolRegistry:
    """
    工具注册中心
    按权限分组管理工具，Agent 根据用户角色动态加载可用工具
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._permission_groups: Dict[str, List[str]] = {
            "user": [],       # 普通用户工具
            "manager": [],    # 管理层工具
            "admin": [],      # 管理员工具
        }

    def register(self, tool: BaseTool) -> None:
        """注册工具"""
        self._tools[tool.name] = tool
        if tool.permission_level in self._permission_groups:
            self._permission_groups[tool.permission_level].append(tool.name)

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """获取指定工具"""
        return self._tools.get(name)

    def get_tools_for_role(self, role: str) -> List[BaseTool]:
        """获取指定角色可用的所有工具"""
        allowed_tools = set()

        # 普通用户工具
        allowed_tools.update(self._permission_groups.get("user", []))

        # 管理层工具
        if role in ("manager", "admin"):
            allowed_tools.update(self._permission_groups.get("manager", []))

        # 管理员工具
        if role == "admin":
            allowed_tools.update(self._permission_groups.get("admin", []))

        return [self._tools[name] for name in allowed_tools if name in self._tools]

    def get_all_tools(self) -> List[BaseTool]:
        """获取所有已注册工具"""
        return list(self._tools.values())

    def get_tool_names(self) -> List[str]:
        """获取所有工具名称"""
        return list(self._tools.keys())


# 全局工具注册中心单例（线程安全）
_registry: Optional[ToolRegistry] = None
_registry_lock = threading.Lock()


def get_tool_registry() -> ToolRegistry:
    """获取全局工具注册中心"""
    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = ToolRegistry()
                _register_default_tools(_registry)
    return _registry


def _register_default_tools(registry: ToolRegistry) -> None:
    """注册默认工具集"""
    from .knowledge_base import KnowledgeBaseTool
    from .database_query import DatabaseQueryTool
    from .ticket_manager import TicketManagerTool
    from .email_summary import EmailSummaryTool
    from .approval_query import ApprovalQueryTool
    from .team_overview import TeamOverviewTool
    from .approval_process import ApprovalProcessTool

    # 常规权限工具
    registry.register(KnowledgeBaseTool())
    registry.register(DatabaseQueryTool())
    registry.register(TicketManagerTool())
    registry.register(EmailSummaryTool())
    registry.register(ApprovalQueryTool())

    # 管理层权限工具
    registry.register(TeamOverviewTool())
    registry.register(ApprovalProcessTool())
