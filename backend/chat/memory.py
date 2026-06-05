"""
记忆管理模块
- 滑动窗口：只保留最近 N 条消息
- 摘要压缩：旧消息压缩为摘要
"""
import threading
from typing import List, Dict, Optional
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import get_settings
from . import crud

logger = logging.getLogger(__name__)


class MemoryManager:
    """记忆管理器"""

    def __init__(self):
        self.settings = get_settings()
        self.window_size = self.settings.HISTORY_WINDOW_SIZE
        self.trigger_count = self.settings.SUMMARY_TRIGGER_COUNT

    async def build_context(
        self,
        db: AsyncSession,
        session_id: int,
        current_message: str,
    ) -> List[Dict[str, str]]:
        """
        构建上下文消息列表

        Args:
            db: 数据库会话
            session_id: 对话 ID
            current_message: 当前用户消息（已保存到 DB）

        Returns:
            消息列表 [{"role": ..., "content": ...}, ...]
            不包含当前用户消息（调用方会单独添加）
        """
        # 获取消息总数
        total_count = await crud.get_message_count(db, session_id)

        # 消息数 <= 窗口大小：直接返回全量（排除最后一条当前消息）
        if total_count <= self.window_size:
            messages = await crud.get_session_messages(db, session_id)
            # 排除最后一条（当前用户消息）
            return [{"role": m.role, "content": m.content} for m in messages[:-1]]

        # 消息数 > 窗口大小：需要滑动窗口 + 摘要
        logger.info(f"Session {session_id}: {total_count} 条消息，启用滑动窗口+摘要")

        # 1. 获取最近 N 条消息
        recent_messages = await crud.get_recent_messages(db, session_id, self.window_size)

        # 2. 获取或生成摘要
        summary = await self._get_or_create_summary(db, session_id, recent_messages[0].id)

        # 3. 构建上下文：摘要 + 最近消息（排除最后一条当前消息）
        context = []
        if summary:
            context.append({
                "role": "system",
                "content": f"[对话历史摘要]\n{summary}"
            })

        # 排除最后一条（当前用户消息）
        for msg in recent_messages[:-1]:
            context.append({"role": msg.role, "content": msg.content})

        return context

    async def _get_or_create_summary(
        self,
        db: AsyncSession,
        session_id: int,
        before_id: int,
    ) -> str:
        """
        获取已有摘要，或为旧消息生成新摘要

        Args:
            db: 数据库会话
            session_id: 对话 ID
            before_id: 只摘要此 ID 之前的消息

        Returns:
            摘要文本
        """
        # 检查是否已有摘要
        session = await crud.get_session(db, session_id, user_id=None)
        if session and session.summary:
            return session.summary

        # 获取旧消息
        old_messages = await crud.get_old_messages(db, session_id, before_id)
        if not old_messages:
            return ""

        # 生成摘要
        summary = await self._generate_summary(old_messages)

        # 保存摘要
        if summary:
            await crud.update_session_summary(db, session_id, summary)
            await db.commit()

        return summary

    async def _generate_summary(self, messages: list) -> str:
        """
        用 LLM 生成对话摘要

        Args:
            messages: 旧消息列表

        Returns:
            摘要文本
        """
        # 构建摘要请求
        history_text = "\n".join(
            f"{'用户' if m.role == 'user' else '助手'}: {m.content[:200]}"
            for m in messages
        )

        prompt = f"""请将以下对话历史压缩为简短摘要（100-200字），保留关键信息：

{history_text}

摘要要求：
1. 保留用户的主要问题和需求
2. 保留重要的结论和决策
3. 忽略细节和重复内容
4. 用第三人称描述"""

        try:
            from backend.agent.core import get_agent
            agent = get_agent()

            # 直接调用 LLM（非流式）
            response = await agent.client.chat.completions.create(
                model=agent.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                stream=False,
            )

            summary = response.choices[0].message.content.strip()
            logger.info(f"生成摘要成功: {summary[:50]}...")
            return summary

        except Exception as e:
            logger.error(f"生成摘要失败: {e}")
            # 降级：取旧消息的前几条作为简单摘要
            return self._fallback_summary(messages)

    def _fallback_summary(self, messages: list) -> str:
        """降级摘要：取前几条消息"""
        summary_parts = []
        for msg in messages[:5]:
            role = "用户" if msg.role == "user" else "助手"
            content = msg.content[:100]
            summary_parts.append(f"{role}: {content}")
        return "早期对话内容：\n" + "\n".join(summary_parts)


# 单例（线程安全）
_memory_manager: Optional[MemoryManager] = None
_memory_lock = threading.Lock()


def get_memory_manager() -> MemoryManager:
    """获取记忆管理器单例"""
    global _memory_manager
    if _memory_manager is None:
        with _memory_lock:
            if _memory_manager is None:
                _memory_manager = MemoryManager()
    return _memory_manager
