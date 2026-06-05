from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
import asyncio
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    fallback_used: bool = False
    needs_confirmation: bool = False  # 高风险操作需要用户确认
    confirmation_message: Optional[str] = None


class BaseTool(ABC):
    """
    工具基类
    内置：重试机制、fallback 降级、高风险操作确认
    """

    def __init__(
        self,
        name: str,
        description: str,
        permission_level: str = "user",  # user, manager, admin
        is_high_risk: bool = False,
        retryable: bool = True,
        max_retries: int = 2,
        fallback_tool: Optional["BaseTool"] = None,
    ):
        self.name = name
        self.description = description
        self.permission_level = permission_level
        self.is_high_risk = is_high_risk
        self.retryable = retryable
        self.max_retries = max_retries
        self.fallback_tool = fallback_tool

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """执行工具逻辑（子类实现）"""
        pass

    async def run(self, **kwargs) -> ToolResult:
        """带重试和降级的执行入口"""
        # 高风险操作需要确认
        if self.is_high_risk and not kwargs.get("_confirmed"):
            return ToolResult(
                success=False,
                needs_confirmation=True,
                confirmation_message=self._get_confirmation_message(**kwargs)
            )

        # 执行重试逻辑
        last_error = None
        for attempt in range(self.max_retries + 1 if self.retryable else 1):
            try:
                result = await self.execute(**kwargs)
                if result.success:
                    if attempt > 0:
                        logger.info(f"工具 {self.name} 第 {attempt + 1} 次尝试成功")
                    return result
                last_error = result.error
                logger.warning(f"工具 {self.name} 执行失败 (attempt {attempt + 1}): {result.error}")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"工具 {self.name} 异常 (attempt {attempt + 1}): {e}")

            # 指数退避
            if attempt < self.max_retries and self.retryable:
                wait_time = 2 ** attempt * 0.5  # 0.5s, 1s, 2s
                logger.info(f"工具 {self.name} 等待 {wait_time}s 后重试")
                await asyncio.sleep(wait_time)

        # 重试失败，尝试 fallback
        if self.fallback_tool:
            logger.info(f"工具 {self.name} 重试失败，使用 fallback: {self.fallback_tool.name}")
            try:
                fallback_result = await self.fallback_tool.execute(**kwargs)
                fallback_result.fallback_used = True
                return fallback_result
            except Exception as e:
                logger.error(f"fallback 工具 {self.fallback_tool.name} 也失败: {e}")

        # 生成友好错误回复
        friendly_error = self._format_friendly_error(last_error)
        logger.error(f"工具 {self.name} 最终失败: {friendly_error}")
        return ToolResult(
            success=False,
            error=friendly_error
        )

    def _get_confirmation_message(self, **kwargs) -> str:
        """生成确认提示消息"""
        return f"即将执行高风险操作: {self.description}，请确认是否继续？"

    def _format_friendly_error(self, error: str) -> str:
        """将技术错误转换为用户友好的提示"""
        error_map = {
            "timeout": "服务响应超时，请稍后再试",
            "connection": "无法连接到服务，请检查网络",
            "permission": "您没有执行此操作的权限",
            "not_found": "未找到相关数据",
        }
        for key, friendly_msg in error_map.items():
            if key in str(error).lower():
                return friendly_msg
        return f"操作失败: {error}，请联系管理员或稍后再试"

    def to_llama_tool(self):
        """转换为 LlamaIndex 工具格式（供 Agent 调用）"""
        from llama_index.core.tools import FunctionTool

        async def tool_fn(**kwargs) -> str:
            result = await self.run(**kwargs)
            if result.needs_confirmation:
                return f"[需要确认] {result.confirmation_message}"
            if not result.success:
                return f"[错误] {result.error}"
            return str(result.data)

        return FunctionTool.from_defaults(
            fn=tool_fn,
            name=self.name,
            description=self.description,
        )
