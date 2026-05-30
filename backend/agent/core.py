from typing import List, Optional, AsyncGenerator, Any
from openai import AsyncOpenAI
import json
import httpx

from .llm_factory import LLMFactory
from .prompt_templates import PromptTemplates
from backend.tools.registry import get_tool_registry
from backend.tools.base import BaseTool, ToolResult


class AgentCore:
    """
    Agent 核心 - 基于 Function Calling
    LLM 决定是否调用工具，我们解析执行，保留 LLM 能力的同时避免幻觉
    """

    def __init__(self):
        self.registry = get_tool_registry()
        self._build_client()

    def _build_client(self):
        """构建 OpenAI 客户端"""
        from backend.config.settings import get_settings
        settings = get_settings()

        if settings.LLM_PROVIDER == "cloud":
            self.api_key = settings.MIMO_API_KEY
            self.base_url = settings.MIMO_API_BASE
            self.model = settings.MIMO_MODEL_NAME
        else:
            self.api_key = "not-needed"
            self.base_url = f"http://localhost:{settings.LOCAL_MODEL_PORT}/v1"
            self.model = settings.LOCAL_MODEL_NAME

        transport = httpx.AsyncHTTPTransport(proxy=None)
        http_client = httpx.AsyncClient(transport=transport, timeout=httpx.Timeout(120.0, connect=30.0))
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            http_client=http_client,
        )

    def _get_tools_schema(self, role: str) -> list[dict]:
        """将工具转换为 OpenAI Function Calling 格式"""
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
        """根据工具类型定义参数 schema"""
        # 为每个工具定义参数
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
        """根据名称获取工具"""
        for tool in self.registry.get_all_tools():
            if tool.name == name:
                return tool
        return None

    async def _execute_tool(self, tool_name: str, arguments: dict) -> str:
        """执行工具并返回结果"""
        tool = self._get_tool_by_name(tool_name)
        if not tool:
            return f"错误：找不到工具 {tool_name}"

        result = await tool.run(**arguments)
        if result.needs_confirmation:
            return f"[需要确认] {result.confirmation_message}"
        if not result.success:
            return f"[错误] {result.error}"
        return str(result.data)

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
        """流式对话 - 基于 Function Calling"""

        # 构建系统提示词
        system_prompt = PromptTemplates.get_system_prompt(
            user_name=user_name,
            department=department,
            role=role,
        )

        # 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": message})

        # 获取工具 schema
        tools_schema = self._get_tools_schema(role)

        try:
            # 第一次调用：让 LLM 决定是否调用工具
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools_schema if tools_schema else None,
                tool_choice="auto",
                max_tokens=2048,
            )

            assistant_msg = response.choices[0].message

            # 检查是否有工具调用
            if assistant_msg.tool_calls:
                # 有工具调用：执行工具，然后让 LLM 生成最终回复
                tool_results = []
                for tool_call in assistant_msg.tool_calls:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}

                    # 执行工具
                    tool_result = await self._execute_tool(func_name, func_args)
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "content": tool_result,
                    })

                # 把工具结果加入消息，让 LLM 生成最终回复
                messages.append(assistant_msg.model_dump())
                messages.extend(tool_results)

                # 第二次调用：LLM 基于工具结果生成回复
                final_response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=2048,
                )

                final_text = final_response.choices[0].message.content or ""
                # 流式输出
                chunk_size = 5
                for i in range(0, len(final_text), chunk_size):
                    yield final_text[i:i + chunk_size]

            else:
                # 无工具调用：直接输出回复
                reply_text = assistant_msg.content or ""
                chunk_size = 5
                for i in range(0, len(reply_text), chunk_size):
                    yield reply_text[i:i + chunk_size]

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"抱歉，处理您的请求时出现问题。请稍后再试或联系管理员。"


# 全局 Agent 实例
_agent: Optional[AgentCore] = None


def get_agent() -> AgentCore:
    """获取全局 Agent 单例"""
    global _agent
    if _agent is None:
        _agent = AgentCore()
    return _agent
