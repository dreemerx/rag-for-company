"""
Agent 核心模块
- 基于 OpenAI Function Calling 实现工具调用
- 支持并行工具执行
- 支持自纠正机制（失败后让 LLM 决定重试或换工具）
- 支持真流式输出
"""
import threading
from typing import List, Optional, AsyncGenerator, Any
from openai import AsyncOpenAI
import json
import httpx
import time
import logging
import asyncio

from .llm_factory import LLMFactory
from .prompt_templates import PromptTemplates
from backend.tools.registry import get_tool_registry
from backend.tools.base import BaseTool, ToolResult
from backend.utils import metrics, alert_manager, audit_log

logger = logging.getLogger(__name__)


class AgentCore:
    """
    Agent 核心类
    - 基于 Function Calling 协议与 LLM 交互
    - 支持并行执行多个工具
    - 工具调用失败后自动进入自纠正循环（最多 2 次）
    """

    # 工具失败后最多自纠正次数
    MAX_SELF_CORRECTION = 2

    def __init__(self):
        """初始化 Agent，获取工具注册中心和 LLM 客户端"""
        self.registry = get_tool_registry()
        self._build_client()

    def _build_client(self):
        """
        构建 OpenAI 兼容客户端
        根据配置选择云端（MiMo）或本地（Qwen）LLM
        """
        from backend.config.settings import get_settings
        settings = get_settings()

        # 根据 LLM_PROVIDER 选择不同的 API 端点
        if settings.LLM_PROVIDER == "cloud":
            self.api_key = settings.MIMO_API_KEY
            self.base_url = settings.MIMO_API_BASE
            self.model = settings.MIMO_MODEL_NAME
        else:
            self.api_key = "not-needed"
            self.base_url = f"http://localhost:{settings.LOCAL_MODEL_PORT}/v1"
            self.model = settings.LOCAL_MODEL_NAME

        # 创建异步 HTTP 客户端，禁用代理，设置超时
        transport = httpx.AsyncHTTPTransport(proxy=None)
        http_client = httpx.AsyncClient(transport=transport, timeout=httpx.Timeout(120.0, connect=30.0))
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            http_client=http_client,
        )

    def _get_tools_schema(self, role: str) -> list[dict]:
        """
        将工具转换为 OpenAI Function Calling 格式

        Args:
            role: 用户角色（user/manager/admin）

        Returns:
            OpenAI 工具 schema 列表
        """
        tools = self.registry.get_tools_for_role(role)
        schemas = []
        for tool in tools:
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": self._get_tool_params(tool),
                }
            })
        return schemas

    def _get_tool_params(self, tool: BaseTool) -> dict:
        """
        根据工具名称定义参数 schema

        Args:
            tool: 工具实例

        Returns:
            OpenAI function parameters 格式的字典
        """
        # 每个工具的参数定义映射表
        params_map = {
            "knowledge_base_search": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"}
                },
                "required": ["query"]
            },
            "database_query": {
                "type": "object",
                "properties": {
                    "query_type": {"type": "string", "enum": ["sales", "customers", "projects", "employees"], "description": "查询类型"}
                },
                "required": ["query_type"]
            },
            "ticket_manager": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["query", "create"], "description": "操作类型"},
                    "ticket_id": {"type": "string", "description": "工单ID（查询单个时使用）"}
                },
                "required": ["action"]
            },
            "email_summary": {
                "type": "object",
                "properties": {
                    "filter_type": {"type": "string", "enum": ["unread", "today", "important"], "description": "筛选类型"}
                },
                "required": []
            },
            "approval_query": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["query", "create"], "description": "操作类型"},
                    "approval_type": {"type": "string", "description": "审批类型（leave/expense/purchase）"}
                },
                "required": ["action"]
            },
            "team_overview": {
                "type": "object",
                "properties": {
                    "query_type": {"type": "string", "enum": ["attendance", "projects", "headcount", "all"], "description": "查询类型"}
                },
                "required": ["query_type"]
            },
            "approval_process": {
                "type": "object",
                "properties": {
                    "approval_id": {"type": "string", "description": "审批单ID"},
                    "action": {"type": "string", "enum": ["approve", "reject"], "description": "操作"},
                    "comment": {"type": "string", "description": "审批意见"}
                },
                "required": ["approval_id", "action"]
            },
        }
        return params_map.get(tool.name, {"type": "object", "properties": {}, "required": []})

    def _get_tool_by_name(self, name: str) -> Optional[BaseTool]:
        """
        根据名称获取工具实例

        Args:
            name: 工具名称

        Returns:
            工具实例，未找到返回 None
        """
        for tool in self.registry.get_all_tools():
            if tool.name == name:
                return tool
        return None

    async def _execute_tool(self, tool_name: str, arguments: dict, user_id: str = None) -> str:
        """
        执行工具并返回结果

        Args:
            tool_name: 工具名称
            arguments: 工具参数
            user_id: 用户 ID（用于审计日志）

        Returns:
            工具执行结果的字符串表示
        """
        tool = self._get_tool_by_name(tool_name)
        if not tool:
            logger.warning(f"找不到工具: {tool_name}")
            return f"错误：找不到工具 {tool_name}"

        start = time.time()
        try:
            # 调用工具（内部包含重试和降级逻辑）
            result = await tool.run(**arguments)
            duration = time.time() - start
            success = result.success and not result.needs_confirmation

            # 记录指标和审计日志
            metrics.record_tool_call(tool_name, duration, success)
            logger.info(f"工具调用 {tool_name} ({duration:.2f}s) success={success}")
            audit_log("tool_call", user_id=user_id, tool=tool_name, duration=round(duration, 2), success=success)

            # 处理需要确认的操作
            if result.needs_confirmation:
                return f"[需要确认] {result.confirmation_message}"
            # 处理执行失败
            if not result.success:
                alert_manager.check_tool_call(tool_name, False)
                return f"[错误] {result.error}"
            return str(result.data)
        except Exception as e:
            duration = time.time() - start
            metrics.record_tool_call(tool_name, duration, False)
            alert_manager.check_tool_call(tool_name, False)
            logger.exception(f"工具调用异常 {tool_name} ({duration:.2f}s)")
            raise

    async def _stream_response(self, messages: list, tools_schema: list = None) -> AsyncGenerator[str, None]:
        """
        真流式输出 - 每个 token 到达即 yield

        Args:
            messages: 消息列表
            tools_schema: 工具 schema 列表

        Yields:
            文本 token 或工具调用标记（JSON 字符串）
        """
        # 调用 LLM 流式接口
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools_schema if tools_schema else None,
            tool_choice="auto",
            max_tokens=2048,
            stream=True,
            stream_options={"include_usage": True},
        )

        # 收集工具调用数据（流式返回时 tool_calls 是分 chunk 到达的）
        tool_calls_data = {}
        has_tool_calls = False
        total_prompt_tokens = 0
        total_completion_tokens = 0

        async for chunk in stream:
            # 记录 token 用量
            if chunk.usage:
                total_prompt_tokens = chunk.usage.prompt_tokens or 0
                total_completion_tokens = chunk.usage.completion_tokens or 0

            choice = chunk.choices[0] if chunk.choices else None
            if not choice:
                continue

            delta = choice.delta

            # 收集 tool_calls（分 chunk 拼装）
            if delta.tool_calls:
                has_tool_calls = True
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in tool_calls_data:
                        tool_calls_data[idx] = {
                            "id": tc_delta.id or "",
                            "function": {"name": "", "arguments": ""},
                        }
                    if tc_delta.id:
                        tool_calls_data[idx]["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            tool_calls_data[idx]["function"]["name"] += tc_delta.function.name
                        if tc_delta.function.arguments:
                            tool_calls_data[idx]["function"]["arguments"] += tc_delta.function.arguments

            # 流式输出文本 token
            if delta.content:
                yield delta.content

            # 工具调用出现时停止文本输出（后续内容属于工具调用元数据）
            if has_tool_calls:
                continue

        # 记录 LLM 调用指标
        metrics.record_llm_call(total_prompt_tokens, total_completion_tokens, success=True)
        alert_manager.check_llm_call(success=True)

        # 如果有工具调用，yield 特殊标记让调用方处理
        if has_tool_calls:
            # 按 index 排序，构建完整的 tool_calls 列表
            sorted_calls = [tool_calls_data[k] for k in sorted(tool_calls_data.keys())]
            yield json.dumps({"__tool_calls__": sorted_calls})

    async def chat_stream(
        self,
        user_id: str,
        session_id: int,
        user_name: str,
        department: str,
        role: str,
        message: str,
        history: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        流式对话入口 - 真流式 + 工具并行 + 自纠正

        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            user_name: 用户姓名
            department: 部门
            role: 角色（user/manager/admin）
            message: 用户消息
            history: 历史消息列表

        Yields:
            流式文本 token
        """
        # 构建系统提示词（根据角色动态附加管理层提示）
        system_prompt = PromptTemplates.get_system_prompt(
            user_name=user_name,
            department=department,
            role=role,
        )

        # 构建完整消息列表
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": message})

        # 根据用户角色获取可用工具 schema
        tools_schema = self._get_tools_schema(role)

        try:
            correction_count = 0
            while True:
                logger.info(f"LLM 调用 user={user_id} session={session_id} model={self.model} correction={correction_count}")

                # 真流式输出
                full_text = ""
                tool_calls_raw = None

                async for chunk in self._stream_response(messages, tools_schema):
                    # 检查是否是工具调用标记
                    if isinstance(chunk, str) and chunk.startswith("{") and '"__tool_calls__"' in chunk:
                        tool_calls_raw = json.loads(chunk)["__tool_calls__"]
                    else:
                        full_text += chunk
                        yield chunk

                # 无工具调用：对话结束
                if not tool_calls_raw:
                    if correction_count > 0:
                        logger.info(f"自纠正成功 user={user_id} 经过 {correction_count} 次修正")
                    return

                # 有工具调用：并行执行
                tool_names = [tc["function"]["name"] for tc in tool_calls_raw]
                logger.info(f"工具调用（并行）: {tool_names}")

                async def _exec_one(tc_data):
                    """执行单个工具并返回结果"""
                    func_name = tc_data["function"]["name"]
                    func_args = json.loads(tc_data["function"]["arguments"]) if tc_data["function"]["arguments"] else {}
                    result_text = await self._execute_tool(func_name, func_args, user_id=user_id)
                    return {
                        "tool_call_id": tc_data["id"],
                        "role": "tool",
                        "content": result_text,
                    }

                # 并行执行所有工具
                tool_results = await asyncio.gather(*[_exec_one(tc) for tc in tool_calls_raw])

                # 检查是否有失败的工具调用
                has_failure = any(
                    r["content"].startswith("[错误]") or r["content"].startswith("[需要确认]")
                    for r in tool_results
                )

                # 构建 assistant 消息（包含 tool_calls 信息）
                assistant_tool_calls = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": tc["function"],
                    }
                    for tc in tool_calls_raw
                ]
                messages.append({"role": "assistant", "content": full_text or None, "tool_calls": assistant_tool_calls})
                messages.extend(tool_results)

                # 全部成功或已达自纠正上限：生成最终回复
                if not has_failure or correction_count >= self.MAX_SELF_CORRECTION:
                    if has_failure:
                        logger.warning(f"工具调用失败，已达自纠正上限 ({self.MAX_SELF_CORRECTION})，生成最终回复")
                    async for chunk in self._stream_response(messages):
                        if not (isinstance(chunk, str) and chunk.startswith("{") and '"__tool_calls__"' in chunk):
                            yield chunk
                    return

                # 有失败且未达上限：继续循环，让 LLM 决定重试或换工具
                correction_count += 1
                logger.info(f"工具调用失败，进入自纠正第 {correction_count} 次")

        except Exception as e:
            # LLM 调用异常处理
            metrics.record_llm_call(success=False)
            alert_manager.check_llm_call(success=False)
            logger.exception(f"LLM 调用异常 user={user_id} session={session_id}")
            yield f"抱歉，处理您的请求时出现问题。请稍后再试或联系管理员。"

    async def chat(
        self,
        user_id: str,
        user_name: str,
        department: str,
        role: str,
        message: str,
        history: list[dict] | None = None,
    ) -> str:
        """
        非流式对话（用于评测等场景）

        Args:
            user_id: 用户 ID
            user_name: 用户名
            department: 部门
            role: 角色
            message: 消息内容
            history: 历史消息

        Returns:
            完整回复文本
        """
        full_reply = ""
        async for chunk in self.chat_stream(
            user_id=user_id,
            session_id=0,
            user_name=user_name,
            department=department,
            role=role,
            message=message,
            history=history,
        ):
            full_reply += chunk
        return full_reply


# 全局 Agent 实例（线程安全，双重检查锁定）
_agent: Optional[AgentCore] = None
_agent_lock = threading.Lock()


def get_agent() -> AgentCore:
    """
    获取全局 Agent 单例

    Returns:
        AgentCore 实例
    """
    global _agent
    if _agent is None:
        with _agent_lock:
            if _agent is None:
                _agent = AgentCore()
    return _agent
