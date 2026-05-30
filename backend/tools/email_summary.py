from typing import Any
from .base import BaseTool, ToolResult


class EmailSummaryTool(BaseTool):
    """邮件摘要工具 - 读取未读邮件，生成摘要"""

    def __init__(self):
        super().__init__(
            name="email_summary",
            description="读取并总结未读邮件，生成邮件摘要。可按发件人、主题、时间等条件筛选。",
            permission_level="user",
            is_high_risk=False,
            retryable=True,
        )

    async def execute(self, filter_type: str = "unread", limit: int = 10, **kwargs) -> ToolResult:
        """
        获取邮件摘要
        Args:
            filter_type: 筛选类型 (unread, today, important)
            limit: 返回数量限制
        """
        try:
            # 模拟邮件数据
            mock_emails = self._get_mock_emails(filter_type, limit)

            if not mock_emails:
                return ToolResult(
                    success=True,
                    data="没有符合条件的邮件。"
                )

            # 生成摘要
            summary = self._generate_summary(mock_emails)
            return ToolResult(success=True, data=summary)

        except Exception as e:
            return ToolResult(success=False, error=f"获取邮件失败: {str(e)}")

    def _get_mock_emails(self, filter_type: str, limit: int) -> list:
        """模拟邮件数据"""
        emails = [
            {
                "from": "hr@company.com",
                "subject": "关于年假政策调整的通知",
                "date": "2024-01-15",
                "preview": "各位同事，根据公司最新规定，年假政策将从下月起调整...",
                "is_important": True,
            },
            {
                "from": "manager@company.com",
                "subject": "本周项目进度汇报",
                "date": "2024-01-15",
                "preview": "请各位在周五前提交本周的项目进度报告...",
                "is_important": False,
            },
            {
                "from": "it@company.com",
                "subject": "系统维护通知",
                "date": "2024-01-14",
                "preview": "本周六凌晨2-6点将进行系统维护...",
                "is_important": True,
            },
        ]

        if filter_type == "unread":
            return emails[:limit]
        elif filter_type == "important":
            return [e for e in emails if e["is_important"]][:limit]
        return emails[:limit]

    def _generate_summary(self, emails: list) -> str:
        """生成邮件摘要"""
        summary_parts = [f"📧 共 {len(emails)} 封邮件:\n"]

        for i, email in enumerate(emails, 1):
            importance = "🔴" if email["is_important"] else "⚪"
            summary_parts.append(
                f"{importance} {i}. 来自: {email['from']}\n"
                f"   主题: {email['subject']}\n"
                f"   时间: {email['date']}\n"
                f"   摘要: {email['preview'][:50]}...\n"
            )

        return "\n".join(summary_parts)
