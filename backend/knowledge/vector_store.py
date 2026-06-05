"""
Milvus 向量数据库管理
- 支持 Milvus Lite（本地文件存储，无需 Docker）
- 支持稠密向量检索
- 支持稀疏向量检索（BM25）
- 支持混合检索
"""
import os
import threading
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
import logging

from pymilvus import MilvusClient

from backend.config.settings import get_settings
from .chunker import Document

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """检索结果"""
    content: str
    metadata: dict
    score: float


class MilvusVectorStore:
    """Milvus 向量数据库管理（使用 Milvus Lite）"""

    def __init__(self):
        self.settings = get_settings()
        self.collection_name = self.settings.MILVUS_COLLECTION_NAME
        self.dimension = self.settings.MILVUS_DIMENSION
        self._client = None
        self._connect()

    def _connect(self):
        """连接 Milvus（使用本地文件存储）"""
        try:
            # 使用 Milvus Lite（本地文件存储）
            db_path = "./data/milvus_lite.db"
            os.makedirs(os.path.dirname(db_path), exist_ok=True)

            self._client = MilvusClient(db_path)
            logger.info(f"Connected to Milvus Lite at {db_path}")

            # 创建集合（如果不存在）
            self._create_collection()

        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            raise

    def _create_collection(self):
        """创建集合"""
        # 检查集合是否存在
        if self._client.has_collection(self.collection_name):
            logger.info(f"Collection {self.collection_name} already exists")
            # 加载集合到内存
            self._client.load_collection(self.collection_name)
            return

        # 创建集合
        self._client.create_collection(
            collection_name=self.collection_name,
            dimension=self.dimension,
            metric_type="COSINE",
            auto_id=True,
        )
        # 加载集合到内存
        self._client.load_collection(self.collection_name)
        logger.info(f"Created collection: {self.collection_name}")

    async def add_documents(
        self,
        documents: List[Document],
        dense_embeddings: List[List[float]],
        sparse_embeddings: List[Dict[int, float]] = None,
    ) -> int:
        """
        添加文档到向量库

        Args:
            documents: 文档列表
            dense_embeddings: 稠密向量列表
            sparse_embeddings: 稀疏向量列表（暂不使用）

        Returns:
            添加的文档数量
        """
        if not documents:
            return 0

        # 准备数据
        data = []
        for i, doc in enumerate(documents):
            # 清理元数据（只保留简单类型）
            clean_metadata = {}
            for k, v in doc.metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_metadata[k] = v
                else:
                    clean_metadata[k] = str(v)

            data.append({
                "vector": dense_embeddings[i],
                "content": doc.page_content,
                "source": clean_metadata.get("source", ""),
                "filename": clean_metadata.get("filename", ""),
                "file_type": clean_metadata.get("file_type", ""),
                "title": clean_metadata.get("title", ""),
                "chunk_index": clean_metadata.get("chunk_index", 0),
                "total_chunks": clean_metadata.get("total_chunks", 1),
                "upload_time": clean_metadata.get("upload_time", ""),
            })

        # 插入数据
        self._client.insert(
            collection_name=self.collection_name,
            data=data,
        )

        logger.info(f"Added {len(documents)} documents to Milvus")
        return len(documents)

    async def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_expr: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        稠密向量检索

        Args:
            query_vector: 查询向量
            top_k: 返回数量
            filter_expr: 过滤表达式

        Returns:
            检索结果列表
        """
        # 检查集合是否有数据
        stats = self._client.get_collection_stats(self.collection_name)
        if int(stats.get("row_count", 0)) == 0:
            return []

        # 检索（Milvus Lite 自动处理 load）
        results = self._client.search(
            collection_name=self.collection_name,
            data=[query_vector],
            limit=top_k,
            output_fields=["content", "source", "filename", "file_type", "title", "chunk_index", "total_chunks", "upload_time"],
            search_params={"metric_type": "COSINE"},
        )

        return self._parse_results(results)

    def _parse_results(self, results) -> List[SearchResult]:
        """解析检索结果"""
        search_results = []

        for hits in results:
            for hit in hits:
                entity = hit.get("entity", {})
                search_results.append(SearchResult(
                    content=entity.get("content", ""),
                    metadata={
                        "source": entity.get("source", ""),
                        "filename": entity.get("filename", ""),
                        "file_type": entity.get("file_type", ""),
                        "title": entity.get("title", ""),
                        "chunk_index": entity.get("chunk_index", 0),
                        "total_chunks": entity.get("total_chunks", 1),
                        "upload_time": entity.get("upload_time", ""),
                    },
                    score=hit.get("distance", 0.0),
                ))

        return search_results

    def get_count(self) -> int:
        """获取文档数量"""
        stats = self._client.get_collection_stats(self.collection_name)
        return int(stats.get("row_count", 0))

    async def delete_by_source(self, source: str) -> int:
        """按来源删除文档"""
        try:
            # 转义特殊字符防止注入
            safe_source = source.replace('\\', '\\\\').replace('"', '\\"')
            self._client.delete(
                collection_name=self.collection_name,
                filter=f'source == "{safe_source}"',
            )
            logger.info(f"Deleted documents from source: {source}")
            return 1
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return 0

    async def clear(self) -> None:
        """清空集合"""
        if self._client.has_collection(self.collection_name):
            self._client.drop_collection(self.collection_name)
            self._create_collection()
            logger.info(f"Cleared collection: {self.collection_name}")

    async def close(self):
        """关闭连接"""
        if self._client:
            self._client.close()


# 单例（线程安全）
_vector_store: Optional[MilvusVectorStore] = None
_vector_store_lock = threading.Lock()


def get_vector_store() -> MilvusVectorStore:
    """获取向量数据库单例"""
    global _vector_store
    if _vector_store is None:
        with _vector_store_lock:
            if _vector_store is None:
                _vector_store = MilvusVectorStore()
    return _vector_store
