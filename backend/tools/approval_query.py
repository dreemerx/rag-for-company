from typing import Any
from .base import BaseTool, ToolResult


class ApprovalQueryTool(BaseTool):
    """审批查询工具 - 查看/发起自己的审批"""

    def __init__(self):
        super().__init__(
            name="approval_query",
            description="查询审批状态、发起新的审批申请。可查看请假、报销、采购等审批流程。",
            permission_level="user",
            is_high_risk=False,
            retryable=True,
        )

    async def execute(self, action: str = "query", approval_type: str = "", **kwargs) -> ToolResult:
        """
        执行审批操作
        Args:
            action: 操作类型 (query, create)
            approval_type: 审批类型 (leave, expense, purchase)
        """
        try:
            if action == "query":
                return await self._query_approvals(approval_type)
            elif action == "create":
                return await self._create_approval(approval_type, **kwargs)
            else:
                return ToolResult(success=False, error=f"不支持的操作: {action}")

        except Exception as e:
            return ToolResult(success=False, error=f"审批操作失败: {str(e)}")

    async def _query_approvals(self, approval_type: str) -> ToolResult:
        """查询审批列表"""
        mock_approvals = [
            {
                "id": "APR-001",
                "type": "请假",
                "status": "待审批",
                "submit_date": "2024-01-15",
                "approver": "李经理",
            },
            {
                "id": "APR-002",
                "type": "报销",
                "status": "已通过",
                "submit_date": "2024-01-10",
                "approver": "王总监",
            },
        ]

        if approval_type:
            mock_approvals = [a for a in mock_approvals if approval_type in a["type"]]

        if not mock_approvals:
            return ToolResult(success=True, data="暂无审批记录")

        # 格式化输出
        result = "审批列表:\n\n"
        for approval in mock_approvals:
            status_icon = "[待审批]" if approval["status"] == "待审批" else "[已通过]"
            result += (
                f"{status_icon} {approval['id']}\n"
                f"   类型: {approval['type']}\n"
                f"   状态: {approval['status']}\n"
                f"   提交时间: {approval['submit_date']}\n"
                f"   审批人: {approval['approver']}\n\n"
            )

        return ToolResult(success=True, data=result)

    async def _create_approval(self, approval_type: str, **kwargs) -> ToolResult:
        """发起新审批"""
        if not approval_type:
            return ToolResult(success=False, error="请指定审批类型")

        return ToolResult(
            success=True,
            data={
                "id": "APR-003",
                "type": approval_type,
                "status": "已提交",
                "message": "审批申请已提交，请等待审批人处理。"
            }
        )
