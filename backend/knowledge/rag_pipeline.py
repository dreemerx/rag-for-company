"""
RAG 完整流水线
- 整合预处理、分块、Embedding、检索、Reranking
- 提供统一的文档入库和检索接口
"""
import threading
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import logging
import time

from backend.config.settings import get_settings
from .preprocessor import get_preprocessor, DocumentPreprocessor
from .chunker import get_chunker, Document, ChunkConfig
from .embedding import get_embedding_manager, EmbeddingManager
from .vector_store import get_vector_store, MilvusVectorStore, SearchResult
from .hybrid_search import get_hybrid_searcher, HybridSearchConfig, SimpleHybridSearcher
from .hyde import get_hyde_searcher, HyDESearcher

logger = logging.getLogger(__name__)


@dataclass
class RAGConfig:
    """RAG 配置"""
    # 分块配置
    chunk_size: int = 500
    chunk_overlap: int = 50
    use_parent_child: bool = False

    # 检索配置
    use_hybrid_search: bool = True
    use_hyde: bool = False
    dense_weight: float = 0.7
    sparse_weight: float = 0.3
    top_k: int = 20
    rerank_top_k: int = 5

    # Reranking 配置
    use_reranker: bool = True  # 启用 Reranker


class RAGPipeline:
    """RAG 流水线"""

    def __init__(self, config: Optional[RAGConfig] = None):
        self.settings = get_settings()
        self.config = config or RAGConfig()

        # 初始化组件
        self.preprocessor = get_preprocessor()
        self.chunker = get_chunker(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            use_parent_child=self.config.use_parent_child,
        )
        self.embedding_manager = get_embedding_manager()
        self.vector_store = get_vector_store()

        # 初始化检索器
        search_config = HybridSearchConfig(
            dense_weight=self.config.dense_weight,
            sparse_weight=self.config.sparse_weight,
            top_k=self.config.top_k,
            rerank_top_k=self.config.rerank_top_k,
            use_reranker=self.config.use_reranker,
        )
        self.hybrid_searcher = get_hybrid_searcher(
            vector_store=self.vector_store,
            embedding_manager=self.embedding_manager,
            config=search_config,
        )

        # HyDE 检索器
        self.hyde_searcher = None
        if self.config.use_hyde:
            self.hyde_searcher = get_hyde_searcher(self.hybrid_searcher)

    async def ingest_file(self, file_path: str) -> Dict[str, Any]:
        """
        入库单个文件

        Args:
            file_path: 文件路径

        Returns:
            入库结果
        """
        start_time = time.time()

        # 1. 加载文档
        from .document_loader import DocumentLoader
        loader = DocumentLoader()
        raw_docs = await loader.load_file(file_path)

        if not raw_docs:
            return {"success": False, "error": "No documents loaded"}

        # 2. 预处理
        processed_docs = self.preprocessor.preprocess_batch(raw_docs)

        # 3. 分块
        all_chunks = []
        for doc in processed_docs:
            chunks = self.chunker.chunk(
                doc.page_content,
                doc.metadata
            )
            all_chunks.extend(chunks)

        if not all_chunks:
            return {"success": False, "error": "No chunks after processing"}

        # 4. 生成 Embedding
        texts = [chunk.page_content for chunk in all_chunks]

        if self.config.use_hybrid_search:
            # 混合检索：同时生成稠密和稀疏向量
            dense_embeddings, sparse_embeddings = self.embedding_manager.embed_hybrid(texts)
        else:
            # 仅稠密向量
            dense_embeddings = self.embedding_manager.embed_dense(texts)
            sparse_embeddings = [{}] * len(texts)

        # 5. 入库
        count = await self.vector_store.add_documents(
            documents=all_chunks,
            dense_embeddings=dense_embeddings,
            sparse_embeddings=sparse_embeddings,
        )

        elapsed = time.time() - start_time

        return {
            "success": True,
            "file": file_path,
            "chunks": count,
            "elapsed_seconds": round(elapsed, 2),
        }

    async def ingest_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        批量入库文件

        Args:
            file_paths: 文件路径列表

        Returns:
            入库结果
        """
        results = []
        total_chunks = 0
        start_time = time.time()

        for file_path in file_paths:
            result = await self.ingest_file(file_path)
            results.append(result)
            if result["success"]:
                total_chunks += result["chunks"]

        elapsed = time.time() - start_time

        return {
            "success": all(r["success"] for r in results),
            "total_files": len(file_paths),
            "total_chunks": total_chunks,
            "elapsed_seconds": round(elapsed, 2),
            "details": results,
        }

    async def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_expr: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        检索

        Args:
            query: 查询文本
            top_k: 返回数量
            filter_expr: 过滤表达式

        Returns:
            检索结果列表
        """
        top_k = top_k or self.config.rerank_top_k

        if self.config.use_hyde and self.hyde_searcher:
            # 使用 HyDE 检索
            return await self.hyde_searcher.search(
                query=query,
                top_k=top_k,
                filter_expr=filter_expr,
            )
        else:
            # 使用混合检索
            return await self.hybrid_searcher.search(
                query=query,
                top_k=top_k,
                filter_expr=filter_expr,
            )

    async def query(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_expr: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        查询（检索 + 生成）

        Args:
            query: 查询文本
            top_k: 返回数量
            filter_expr: 过滤表达式

        Returns:
            查询结果
        """
        # 1. 检索
        search_results = await self.search(query, top_k, filter_expr)

        # 2. 构建上下文
        contexts = [r.content for r in search_results]

        # 3. 构建元数据
        metadata = [r.metadata for r in search_results]

        return {
            "query": query,
            "contexts": contexts,
            "metadata": metadata,
            "scores": [r.score for r in search_results],
        }

    async def clear(self) -> None:
        """清空知识库"""
        await self.vector_store.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "document_count": self.vector_store.get_count(),
            "config": {
                "chunk_size": self.config.chunk_size,
                "chunk_overlap": self.config.chunk_overlap,
                "use_hybrid_search": self.config.use_hybrid_search,
                "use_hyde": self.config.use_hyde,
                "use_reranker": self.config.use_reranker,
            }
        }


# 单例（线程安全）
_pipeline: Optional[RAGPipeline] = None
_pipeline_lock = threading.Lock()


def get_rag_pipeline(config: Optional[RAGConfig] = None) -> RAGPipeline:
    """获取 RAG 流水线单例"""
    global _pipeline
    if _pipeline is None:
        with _pipeline_lock:
            if _pipeline is None:
                _pipeline = RAGPipeline(config)
    return _pipeline
