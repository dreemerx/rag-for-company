from typing import List, Optional, AsyncGenerator
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import BaseTool as LlamaBaseTool
from llama_index.core.llms import ChatMessage, MessageRole

from .llm_factory import LLMFactory
from .prompt_templates import PromptTemplates
from backend.tools.registry import get_tool_registry, ToolRegistry
from backend.tools.base import BaseTool


class AgentCore:
    """
    Agent 核心
    基于 LlamaIndex ReActAgent，集成工具系统和会话管理

    隔离策略：
    - 每个用户的每个对话独立创建 Agent 实例
    - key 格式: "{user_id}_{session_id}"
    - 切换对话时创建新 Agent，上下文完全隔离
    """

    def __init__(self):
        self.llm = LLMFactory.create()
        self.registry = get_tool_registry()
        self._agents: dict[str, ReActAgent] = {}

    def _make_key(self, user_id: str, session_id: int) -> str:
        """生成 Agent 缓存 key"""
        return f"{user_id}_{session_id}"

    def get_agent(
        self,
        user_id: str,
        session_id: int,
        user_name: str,
        department: str,
        role: str,
        history: list[dict] | None = None,
    ) -> ReActAgent:
        """获取或创建 Agent 实例（按 user_id + session_id 隔离）"""

        key = self._make_key(user_id, session_id)

        if key not in self._agents:
            # 根据用户角色获取可用工具
            tools = self.registry.get_tools_for_role(role)
            llama_tools = [t.to_llama_tool() for t in tools]

            # 构建系统提示词
            system_prompt = PromptTemplates.get_system_prompt(
                user_name=user_name,
                department=department,
                role=role,
            )

            # 创建 Agent
            agent = ReActAgent(
                tools=llama_tools,
                llm=self.llm,
                system_prompt=system_prompt,
                verbose=True,
            )

            # 注入历史消息到 Agent 内存
            if history:
                for msg in history:
                    role_enum = MessageRole.USER if msg["role"] == "user" else MessageRole.ASSISTANT
                    agent.memory.put(ChatMessage(role=role_enum, content=msg["content"]))

            self._agents[key] = agent

        return self._agents[key]

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
        """流式处理用户消息"""
        agent = self.get_agent(
            user_id=user_id,
            session_id=session_id,
            user_name=user_name,
            department=department,
            role=role,
            history=history,
        )

        try:
            response = await agent.run(message)
            full_text = str(response)

            chunk_size = 5
            for i in range(0, len(full_text), chunk_size):
                yield full_text[i:i + chunk_size]

        except Exception as e:
            yield f"抱歉，处理您的请求时出现问题: {str(e)}。请稍后再试或联系管理员。"

    def clear_session(self, user_id: str, session_id: int) -> None:
        """清除指定会话的 Agent"""
        key = self._make_key(user_id, session_id)
        if key in self._agents:
            del self._agents[key]

    def clear_user(self, user_id: str) -> None:
        """清除用户的所有 Agent"""
        keys_to_delete = [k for k in self._agents if k.startswith(f"{user_id}_")]
        for key in keys_to_delete:
            del self._agents[key]


# 全局 Agent 实例
_agent: Optional[AgentCore] = None


def get_agent() -> AgentCore:
    """获取全局 Agent 单例"""
    global _agent
    if _agent is None:
        _agent = AgentCore()
    return _agent
