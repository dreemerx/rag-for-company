"""
Hybrid Search 模块
- 结合稠密向量检索和稀疏向量检索（BM25）
- 支持权重配置
- 集成 Reranking
"""
from typing import List, Optional, Tuple
from dataclasses import dataclass
import logging

from backend.config.settings import get_settings
from .vector_store import MilvusVectorStore, SearchResult
from .embedding import EmbeddingManager
from .reranker import Reranker, get_reranker

logger = logging.getLogger(__name__)


@dataclass
class HybridSearchConfig:
    """混合检索配置"""
    dense_weight: float = 0.7
    sparse_weight: float = 0.3
    top_k: int = 20  # 初筛数量
    rerank_top_k: int = 5  # 重排序后返回数量
    use_reranker: bool = True  # 启用 Reranker


class HybridSearcher:
    """混合检索器"""

    def __init__(
        self,
        vector_store: MilvusVectorStore,
        embedding_manager: EmbeddingManager,
        reranker: Optional[Reranker] = None,
        config: Optional[HybridSearchConfig] = None,
    ):
        self.vector_store = vector_store
        self.embedding_manager = embedding_manager
        self.reranker = reranker
        self.config = config or HybridSearchConfig()

    async def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_expr: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        混合检索

        Args:
            query: 查询文本
            top_k: 返回数量
            filter_expr: 过滤表达式

        Returns:
            检索结果列表
        """
        top_k = top_k or self.config.rerank_top_k

        # 1. 编码查询
        dense_vector, sparse_vector = self.embedding_manager.embed_query(query)

        # 2. 混合检索
        search_results = await self.vector_store.search_hybrid(
            dense_vector=dense_vector,
            sparse_vector=sparse_vector,
            top_k=self.config.top_k,
            dense_weight=self.config.dense_weight,
            sparse_weight=self.config.sparse_weight,
            filter_expr=filter_expr,
        )

        # 3. Reranking
        if self.config.use_reranker and self.reranker and len(search_results) > top_k:
            search_results = await self._rerank(query, search_results, top_k)

        return search_results[:top_k]

    async def _rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: int,
    ) -> List[SearchResult]:
        """重排序"""
        # 转换为 Reranker 输入格式
        documents = [
            (r.content, r.metadata, r.score)
            for r in results
        ]

        # 重排序
        rerank_results = self.reranker.rerank(
            query=query,
            documents=documents,
            top_k=top_k,
        )

        # 转换回 SearchResult
        return [
            SearchResult(
                content=r.content,
                metadata=r.metadata,
                score=r.score,
            )
            for r in rerank_results
        ]


class SimpleHybridSearcher:
    """
    简化版混合检索器（不依赖 BM25 模型）
    使用 Milvus 内置的稀疏向量支持
    """

    def __init__(
        self,
        vector_store: MilvusVectorStore,
        embedding_manager: EmbeddingManager,
        config: Optional[HybridSearchConfig] = None,
    ):
        self.vector_store = vector_store
        self.embedding_manager = embedding_manager
        self.config = config or HybridSearchConfig()
        self._reranker = None

    def _get_reranker(self):
        """延迟加载 Reranker"""
        if self._reranker is None and self.config.use_reranker:
            self._reranker = get_reranker()
        return self._reranker

    async def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_expr: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        混合检索

        Args:
            query: 查询文本
            top_k: 返回数量
            filter_expr: 过滤表达式

        Returns:
            检索结果列表
        """
        top_k = top_k or self.config.rerank_top_k

        # 1. 编码查询（使用 BGE-M3 同时生成 dense 和 sparse）
        dense_vector, sparse_vector = self.embedding_manager.embed_query(query)

        # 2. 向量检索
        results = await self.vector_store.search(
            query_vector=dense_vector,
            top_k=self.config.top_k,
            filter_expr=filter_expr,
        )

        # 3. Reranking
        reranker = self._get_reranker()
        if reranker and len(results) > top_k:
            documents = [(r.content, r.metadata, r.score) for r in results]
            rerank_results = reranker.rerank(query, documents, top_k)
            results = [
                SearchResult(content=r.content, metadata=r.metadata, score=r.score)
                for r in rerank_results
            ]

        return results[:top_k]


# 工厂函数
def get_hybrid_searcher(
    vector_store: Optional[MilvusVectorStore] = None,
    embedding_manager: Optional[EmbeddingManager] = None,
    config: Optional[HybridSearchConfig] = None,
) -> SimpleHybridSearcher:
    """获取混合检索器"""
    from .vector_store import get_vector_store
    from .embedding import get_embedding_manager

    return SimpleHybridSearcher(
        vector_store=vector_store or get_vector_store(),
        embedding_manager=embedding_manager or get_embedding_manager(),
        config=config,
    )
