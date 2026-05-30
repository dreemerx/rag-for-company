import os
from typing import List, Optional
from dataclasses import dataclass
import chromadb
from chromadb.config import Settings

from backend.config.settings import get_settings


@dataclass
class Document:
    """文档数据结构"""
    page_content: str
    metadata: dict


class VectorStore:
    """Chroma 向量数据库管理"""

    def __init__(self):
        settings = get_settings()
        self.persist_dir = settings.CHROMA_PERSIST_DIR
        self.collection_name = settings.CHROMA_COLLECTION_NAME

        # 确保目录存在
        os.makedirs(self.persist_dir, exist_ok=True)

        # 初始化 Chroma 客户端
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )

        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    async def add_documents(self, documents: List[Document]) -> int:
        """添加文档到向量库"""
        if not documents:
            return 0

        ids = [f"doc_{i}" for i in range(len(documents))]
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]

        # Chroma 会自动处理 embedding
        self.collection.add(
            documents=texts,
            metadatas=metadatas,
            ids=ids,
        )

        return len(documents)

    async def search(self, query: str, top_k: int = 5) -> List[Document]:
        """检索相似文档"""
        if self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=min(top_k, self.collection.count()),
        )

        documents = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                documents.append(Document(
                    page_content=doc,
                    metadata=metadata,
                ))

        return documents

    async def delete_by_source(self, source: str) -> int:
        """按来源删除文档"""
        try:
            self.collection.delete(
                where={"source": source}
            )
            return 1
        except Exception:
            return 0

    def get_count(self) -> int:
        """获取文档数量"""
        return self.collection.count()

    async def clear(self) -> None:
        """清空集合"""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )


# 单例
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """获取向量数据库单例"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
