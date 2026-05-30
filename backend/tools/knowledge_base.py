from typing import Any
from .base import BaseTool, ToolResult


class KnowledgeBaseTool(BaseTool):
    """知识库检索工具 - 检索公司制度、流程、手册等"""

    def __init__(self):
        super().__init__(
            name="knowledge_base_search",
            description="检索公司内部知识库，包括公司制度、流程、手册、常见问题等。适用于查询公司政策、工作流程、规章制度等问题。",
            permission_level="user",
            is_high_risk=False,
            retryable=True,
        )

    async def execute(self, query: str = "", **kwargs) -> ToolResult:
        """
        执行知识库检索
        Args:
            query: 检索关键词或问题
        """
        if not query:
            return ToolResult(success=False, error="请提供检索关键词")

        try:
            # 从向量数据库检索
            from backend.knowledge.vector_store import get_vector_store
            vector_store = get_vector_store()
            results = await vector_store.search(query, top_k=5)

            if not results:
                return ToolResult(
                    success=True,
                    data="未找到相关知识库内容，请尝试换个关键词或联系管理员。"
                )

            # 格式化检索结果
            formatted_results = []
            for i, doc in enumerate(results, 1):
                formatted_results.append(
                    f"【结果{i}】\n"
                    f"来源: {doc.metadata.get('source', '未知')}\n"
                    f"内容: {doc.page_content}\n"
                )

            return ToolResult(
                success=True,
                data="\n".join(formatted_results)
            )

        except Exception as e:
            return ToolResult(success=False, error=f"知识库检索失败: {str(e)}")
