from typing import Any
from .base import BaseTool, ToolResult


class ApprovalProcessTool(BaseTool):
    """审批流处理工具 - 在对话中批准/驳回申请（管理层权限）"""

    def __init__(self):
        super().__init__(
            name="approval_process",
            description="处理审批申请，可以直接在对话中批准或驳回申请。仅管理层可使用。高风险操作需要确认。",
            permission_level="manager",
            is_high_risk=True,  # 高风险操作
            retryable=True,
        )

    async def execute(
        self,
        approval_id: str = "",
        action: str = "",  # approve, reject
        comment: str = "",
        **kwargs
    ) -> ToolResult:
        """
        处理审批
        Args:
            approval_id: 审批单ID
            action: 操作 (approve, reject)
            comment: 审批意见
        """
        if not approval_id:
            return ToolResult(success=False, error="请提供审批单ID")

        if action not in ("approve", "reject"):
            return ToolResult(success=False, error="请指定操作类型: approve 或 reject")

        try:
            # 模拟审批处理
            result = await self._process_approval(approval_id, action, comment)
            return ToolResult(success=True, data=result)

        except Exception as e:
            return ToolResult(success=False, error=f"审批处理失败: {str(e)}")

    async def _process_approval(
        self,
        approval_id: str,
        action: str,
        comment: str
    ) -> dict:
        """处理审批请求"""
        action_text = "批准" if action == "approve" else "驳回"

        return {
            "approval_id": approval_id,
            "action": action_text,
            "comment": comment,
            "status": "已处理",
            "message": f"审批单 {approval_id} 已{action_text}",
        }

    def _get_confirmation_message(self, **kwargs) -> str:
        """生成确认提示"""
        action = kwargs.get("action", "")
        approval_id = kwargs.get("approval_id", "")

        if action == "approve":
            return f"确认要批准审批单 {approval_id} 吗？此操作不可撤销。"
        elif action == "reject":
            return f"确认要驳回审批单 {approval_id} 吗？此操作不可撤销。"
        return super()._get_confirmation_message(**kwargs)
