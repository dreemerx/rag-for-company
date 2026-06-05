"""
知识库检索工具
- 使用 RAG 流水线进行检索
- 支持混合检索、HyDE、Reranking
"""
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

    async def execute(self, query: str = "", top_k: int = 5, **kwargs) -> ToolResult:
        """
        执行知识库检索

        Args:
            query: 检索关键词或问题
            top_k: 返回结果数量
        """
        if not query:
            return ToolResult(success=False, error="请提供检索关键词")

        try:
            # 使用 RAG 流水线检索
            from backend.knowledge.rag_pipeline import get_rag_pipeline
            pipeline = get_rag_pipeline()

            results = await pipeline.search(query, top_k=top_k)

            if not results:
                return ToolResult(
                    success=True,
                    data="未找到相关知识库内容，请尝试换个关键词或联系管理员。"
                )

            # 格式化检索结果
            formatted_results = []
            for i, result in enumerate(results, 1):
                source = result.metadata.get('source', '未知')
                filename = result.metadata.get('filename', '')
                title = result.metadata.get('title', '')

                # 显示来源信息
                source_info = filename or source
                if title:
                    source_info = f"{title} ({source_info})"

                formatted_results.append(
                    f"【结果{i}】(相关度: {result.score:.2f})\n"
                    f"来源: {source_info}\n"
                    f"内容: {result.content}\n"
                )

            return ToolResult(
                success=True,
                data="\n".join(formatted_results)
            )

        except Exception as e:
            return ToolResult(success=False, error=f"知识库检索失败: {str(e)}")


class KnowledgeBaseStatsTool(BaseTool):
    """知识库统计工具"""

    def __init__(self):
        super().__init__(
            name="knowledge_base_stats",
            description="获取知识库统计信息，包括文档数量、配置等。",
            permission_level="user",
            is_high_risk=False,
            retryable=True,
        )

    async def execute(self, **kwargs) -> ToolResult:
        """获取知识库统计"""
        try:
            from backend.knowledge.rag_pipeline import get_rag_pipeline
            pipeline = get_rag_pipeline()

            stats = pipeline.get_stats()

            return ToolResult(
                success=True,
                data=f"知识库统计:\n"
                     f"- 文档块数量: {stats['document_count']}\n"
                     f"- 分块大小: {stats['config']['chunk_size']} 字符\n"
                     f"- 混合检索: {'启用' if stats['config']['use_hybrid_search'] else '禁用'}\n"
                     f"- HyDE: {'启用' if stats['config']['use_hyde'] else '禁用'}\n"
                     f"- Reranking: {'启用' if stats['config']['use_reranker'] else '禁用'}"
            )

        except Exception as e:
            return ToolResult(success=False, error=f"获取统计信息失败: {str(e)}")
