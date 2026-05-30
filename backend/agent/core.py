from typing import List, Optional
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
    """

    def __init__(self):
        self.llm = LLMFactory.create()
        self.registry = get_tool_registry()
        self._sessions: dict[str, ReActAgent] = {}

    def get_agent_for_user(
        self,
        user_id: str,
        user_name: str,
        department: str,
        role: str,
    ) -> ReActAgent:
        """获取或创建用户的 Agent 实例"""

        if user_id not in self._sessions:
            # 根据用户角色获取可用工具
            tools = self.registry.get_tools_for_role(role)
            llama_tools = [t.to_llama_tool() for t in tools]

            # 构建系统提示词
            system_prompt = PromptTemplates.get_system_prompt(
                user_name=user_name,
                department=department,
                role=role,
            )

            # 创建 Agent (新版 LlamaIndex API)
            agent = ReActAgent(
                tools=llama_tools,
                llm=self.llm,
                system_prompt=system_prompt,
                verbose=True,
            )

            self._sessions[user_id] = agent

        return self._sessions[user_id]

    async def chat(
        self,
        user_id: str,
        user_name: str,
        department: str,
        role: str,
        message: str,
    ) -> str:
        """处理用户消息"""
        agent = self.get_agent_for_user(
            user_id=user_id,
            user_name=user_name,
            department=department,
            role=role,
        )

        try:
            # 新版 LlamaIndex 使用 run 方法
            response = await agent.run(message)
            return str(response)
        except Exception as e:
            return f"抱歉，处理您的请求时出现问题: {str(e)}。请稍后再试或联系管理员。"

    def clear_session(self, user_id: str) -> None:
        """清除用户会话"""
        if user_id in self._sessions:
            del self._sessions[user_id]

    def get_session_history(self, user_id: str) -> List[ChatMessage]:
        """获取用户会话历史"""
        if user_id in self._sessions:
            agent = self._sessions[user_id]
            return agent.memory.get_all() if hasattr(agent, 'memory') else []
        return []


# 全局 Agent 实例
_agent: Optional[AgentCore] = None


def get_agent() -> AgentCore:
    """获取全局 Agent 单例"""
    global _agent
    if _agent is None:
        _agent = AgentCore()
    return _agent
