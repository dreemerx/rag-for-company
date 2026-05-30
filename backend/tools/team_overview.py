from typing import Any
from .base import BaseTool, ToolResult


class TeamOverviewTool(BaseTool):
    """团队概览工具 - 查考勤、项目进度、团队人数（管理层权限）"""

    def __init__(self):
        super().__init__(
            name="team_overview",
            description="查看团队概览信息，包括考勤统计、项目进度、团队人数等。仅管理层可使用。",
            permission_level="manager",
            is_high_risk=False,
            retryable=True,
        )

    async def execute(self, query_type: str = "all", team_id: str = "", **kwargs) -> ToolResult:
        """
        查询团队概览
        Args:
            query_type: 查询类型 (attendance, projects, headcount, all)
            team_id: 团队ID（可选）
        """
        try:
            if query_type == "attendance":
                return await self._get_attendance(team_id)
            elif query_type == "projects":
                return await self._get_project_progress(team_id)
            elif query_type == "headcount":
                return await self._get_headcount(team_id)
            else:
                return await self._get_all_overview(team_id)

        except Exception as e:
            return ToolResult(success=False, error=f"查询团队信息失败: {str(e)}")

    async def _get_attendance(self, team_id: str) -> ToolResult:
        """获取考勤统计"""
        data = {
            "period": "2024年1月",
            "team": team_id or "全部门",
            "total_employees": 45,
            "attendance_rate": "96.5%",
            "late_count": 8,
            "early_leave_count": 3,
            "absent_count": 2,
        }
        return ToolResult(success=True, data=data)

    async def _get_project_progress(self, team_id: str) -> ToolResult:
        """获取项目进度"""
        data = {
            "team": team_id or "全部门",
            "total_projects": 12,
            "on_track": 8,
            "at_risk": 3,
            "delayed": 1,
            "completion_rate": "78%",
            "projects": [
                {"name": "项目A", "progress": "85%", "status": "正常"},
                {"name": "项目B", "progress": "60%", "status": "风险"},
                {"name": "项目C", "progress": "45%", "status": "延期"},
            ]
        }
        return ToolResult(success=True, data=data)

    async def _get_headcount(self, team_id: str) -> ToolResult:
        """获取团队人数"""
        data = {
            "team": team_id or "全部门",
            "total": 45,
            "active": 43,
            "on_leave": 2,
            "new_hires_this_month": 3,
            "turnover_rate": "4.5%",
        }
        return ToolResult(success=True, data=data)

    async def _get_all_overview(self, team_id: str) -> ToolResult:
        """获取全部概览"""
        attendance = await self._get_attendance(team_id)
        projects = await self._get_project_progress(team_id)
        headcount = await self._get_headcount(team_id)

        return ToolResult(
            success=True,
            data={
                "attendance": attendance.data,
                "projects": projects.data,
                "headcount": headcount.data,
            }
        )
