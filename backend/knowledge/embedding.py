"""
Embedding 模块
- 使用 sentence-transformers 本地模型
- 支持稠密向量生成
"""
import threading
from typing import List, Dict, Optional, Tuple
import logging

from backend.config.settings import get_settings

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """Embedding 管理器"""

    def __init__(self):
        self.settings = get_settings()
        self._model = None
        self._model_lock = threading.Lock()

    def _load_model(self):
        """加载模型（线程安全）"""
        if self._model is not None:
            return

        with self._model_lock:
            if self._model is not None:
                return

            try:
                from sentence_transformers import SentenceTransformer

                model_name = self.settings.EMBEDDING_MODEL
                logger.info(f"Loading embedding model: {model_name}")

                self._model = SentenceTransformer(model_name)
                logger.info(f"Loaded embedding model: {model_name}, dim={self._model.get_sentence_embedding_dimension()}")

            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                raise

    def embed_dense(self, texts: List[str]) -> List[List[float]]:
        """
        生成稠密向量

        Args:
            texts: 文本列表

        Returns:
            向量列表
        """
        if not texts:
            return []

        self._load_model()

        embeddings = self._model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,
        )

        return embeddings.tolist()

    def embed_query(self, query: str) -> Tuple[List[float], Dict[int, float]]:
        """
        编码查询

        Args:
            query: 查询文本

        Returns:
            (dense_vector, sparse_vector)
        """
        self._load_model()

        embedding = self._model.encode(
            [query],
            normalize_embeddings=True,
        )

        dense = embedding[0].tolist()
        sparse = {}  # 简化版不使用稀疏向量

        return dense, sparse

    def embed_hybrid(self, texts: List[str]) -> Tuple[List[List[float]], List[Dict[int, float]]]:
        """
        生成混合向量（稠密 + 稀疏）

        Args:
            texts: 文本列表

        Returns:
            (dense_embeddings, sparse_embeddings)
        """
        if not texts:
            return [], []

        dense_embeddings = self.embed_dense(texts)
        sparse_embeddings = [{}] * len(texts)

        return dense_embeddings, sparse_embeddings

    def get_dimension(self) -> int:
        """获取向量维度"""
        self._load_model()
        return self._model.get_sentence_embedding_dimension()


# 单例（线程安全）
_embedding_manager: Optional[EmbeddingManager] = None
_embedding_lock = threading.Lock()


def get_embedding_manager() -> EmbeddingManager:
    """获取 Embedding 管理器单例"""
    global _embedding_manager
    if _embedding_manager is None:
        with _embedding_lock:
            if _embedding_manager is None:
                _embedding_manager = EmbeddingManager()
    return _embedding_manager
