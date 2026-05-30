from typing import Any
from .base import BaseTool, ToolResult


class DatabaseQueryTool(BaseTool):
    """数据库查询工具 - 查询业务数据、生成报表"""

    def __init__(self):
        super().__init__(
            name="database_query",
            description="查询公司业务数据库，可查询销售数据、客户信息、项目进度等。支持生成简单的统计报表。",
            permission_level="user",
            is_high_risk=False,
            retryable=True,
        )

    async def execute(self, query_type: str = "", params: dict = None, **kwargs) -> ToolResult:
        """
        执行数据库查询
        Args:
            query_type: 查询类型 (sales, customers, projects, etc.)
            params: 查询参数
        """
        if not query_type:
            return ToolResult(success=False, error="请指定查询类型")

        params = params or {}

        try:
            # 模拟数据库查询（实际项目中应连接真实数据库）
            mock_data = self._get_mock_data(query_type, params)

            if not mock_data:
                return ToolResult(
                    success=True,
                    data="未找到相关数据，建议使用知识库检索相关信息。"
                )

            return ToolResult(success=True, data=mock_data)

        except Exception as e:
            return ToolResult(success=False, error=f"数据库查询失败: {str(e)}")

    def _get_mock_data(self, query_type: str, params: dict) -> Any:
        """模拟数据（开发阶段使用）"""
        mock_responses = {
            "sales": "本月销售总额: ¥1,234,567\n环比增长: 12.5%\nTop客户: XX公司、YY集团",
            "customers": "活跃客户数: 156\n新增客户: 23\n流失客户: 5",
            "projects": "进行中项目: 12个\n已完成项目: 8个\n延期项目: 2个",
            "employees": "在职员工: 234人\n本月新入职: 15人\n离职: 3人",
        }
        return mock_responses.get(query_type, f"暂不支持查询类型: {query_type}")
