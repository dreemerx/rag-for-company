"""
Reranking 模块
- 使用 Cross-Encoder 模型对检索结果重排序
- 支持本地模型和 API 两种方式
"""
from typing import List, Optional, Tuple
from dataclasses import dataclass
import logging

from backend.config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class RerankResult:
    """重排序结果"""
    content: str
    metadata: dict
    score: float
    original_score: float


class Reranker:
    """Reranker 基类"""

    def rerank(
        self,
        query: str,
        documents: List[Tuple[str, dict, float]],
        top_k: int = 5,
    ) -> List[RerankResult]:
        """重排序"""
        raise NotImplementedError


class CrossEncoderReranker(Reranker):
    """
    Cross-Encoder Reranker
    使用 sentence-transformers 的 CrossEncoder 模型
    """

    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None):
        self.settings = get_settings()
        # 默认使用多语言 Cross-Encoder 模型
        self.model_name = model_name or "BAAI/bge-reranker-base"
        self.device = device or self.settings.EMBEDDING_DEVICE
        self._model = None

    def _load_model(self):
        """延迟加载模型"""
        if self._model is not None:
            return

        try:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(
                self.model_name,
                max_length=512,
                device=self.device,
            )
            logger.info(f"Loaded CrossEncoder reranker: {self.model_name}")
        except ImportError:
            logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"Failed to load reranker model: {e}")
            raise

    def rerank(
        self,
        query: str,
        documents: List[Tuple[str, dict, float]],
        top_k: int = 5,
    ) -> List[RerankResult]:
        """重排序"""
        if not documents:
            return []

        self._load_model()

        # 构造查询-文档对
        pairs = [[query, doc[0]] for doc in documents]

        # 计算相关性分数
        scores = self._model.predict(pairs)

        # 合并结果
        results = []
        for i, (content, metadata, original_score) in enumerate(documents):
            results.append(RerankResult(
                content=content,
                metadata=metadata,
                score=float(scores[i]),
                original_score=original_score,
            ))

        # 按新分数排序
        results.sort(key=lambda x: x.score, reverse=True)

        return results[:top_k]


class SimpleReranker(Reranker):
    """
    简单 Reranker（基于关键词匹配）
    当 Cross-Encoder 不可用时的降级方案
    """

    def rerank(
        self,
        query: str,
        documents: List[Tuple[str, dict, float]],
        top_k: int = 5,
    ) -> List[RerankResult]:
        """基于关键词重排序"""
        if not documents:
            return []

        # 简单关键词匹配评分
        query_chars = set(query)
        results = []
        for content, metadata, original_score in documents:
            content_chars = set(content)
            overlap = len(query_chars & content_chars)
            keyword_score = overlap / max(len(query_chars), 1)
            # 综合分数：原始分数 + 关键词匹配
            combined_score = original_score * 0.6 + keyword_score * 0.4
            results.append(RerankResult(
                content=content,
                metadata=metadata,
                score=combined_score,
                original_score=original_score,
            ))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]


class APIReranker(Reranker):
    """API Reranker（适用于在线服务）"""

    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        self.settings = get_settings()
        self.api_url = api_url or f"{self.settings.MIMO_API_BASE}/rerank"
        self.api_key = api_key or self.settings.MIMO_API_KEY

    def rerank(
        self,
        query: str,
        documents: List[Tuple[str, dict, float]],
        top_k: int = 5,
    ) -> List[RerankResult]:
        """通过 API 重排序"""
        import httpx

        if not documents:
            return []

        # 构造请求
        texts = [doc[0] for doc in documents]
        payload = {
            "model": "bge-reranker-v2-m3",
            "query": query,
            "documents": texts,
            "top_n": top_k,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = httpx.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            result = response.json()

            # 解析结果
            rerank_results = []
            for item in result.get("results", []):
                idx = item["index"]
                content, metadata, original_score = documents[idx]
                rerank_results.append(RerankResult(
                    content=content,
                    metadata=metadata,
                    score=item["relevance_score"],
                    original_score=original_score,
                ))

            return rerank_results

        except Exception as e:
            logger.error(f"Reranker API failed: {e}")
            # 降级：返回原始排序
            return [
                RerankResult(
                    content=doc[0],
                    metadata=doc[1],
                    score=doc[2],
                    original_score=doc[2],
                )
                for doc in documents[:top_k]
            ]


# 单例
_reranker: Optional[Reranker] = None


def get_reranker(use_api: bool = False, use_simple: bool = False) -> Reranker:
    """
    获取 Reranker 单例

    Args:
        use_api: 使用 API Reranker
        use_simple: 使用简单关键词 Reranker（无需模型）
    """
    global _reranker
    if _reranker is None:
        if use_api:
            _reranker = APIReranker()
        elif use_simple:
            _reranker = SimpleReranker()
        else:
            try:
                _reranker = CrossEncoderReranker()
            except Exception as e:
                logger.warning(f"CrossEncoder 加载失败，降级到简单 Reranker: {e}")
                _reranker = SimpleReranker()
    return _reranker
