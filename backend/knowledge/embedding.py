from typing import Optional
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.embeddings import BaseEmbedding

from backend.config.settings import get_settings


class EmbeddingManager:
    """Embedding 模型管理"""

    def __init__(self):
        self._embed_model: Optional[BaseEmbedding] = None

    def get_embedding_model(self) -> BaseEmbedding:
        """获取 Embedding 模型"""
        if self._embed_model is None:
            settings = get_settings()
            # 使用 OpenAI 兼容的 Embedding API
            self._embed_model = OpenAIEmbedding(
                model_name="text-embedding-ada-002",
                api_key=settings.MIMO_API_KEY if settings.LLM_PROVIDER == "cloud" else "not-needed",
                api_base=settings.MIMO_API_BASE if settings.LLM_PROVIDER == "cloud" else f"http://localhost:{settings.LOCAL_MODEL_PORT}/v1",
            )
        return self._embed_model


# 单例
_embedding_manager: Optional[EmbeddingManager] = None


def get_embedding_manager() -> EmbeddingManager:
    """获取 Embedding 管理器单例"""
    global _embedding_manager
    if _embedding_manager is None:
        _embedding_manager = EmbeddingManager()
    return _embedding_manager
