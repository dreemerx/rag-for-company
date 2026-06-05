"""
HyDE (Hypothetical Document Embeddings) 模块
- 让 LLM 生成假设性文档
- 用假设文档的向量进行检索
- 提升检索召回率
"""
from typing import List, Optional
import logging

from backend.config.settings import get_settings

logger = logging.getLogger(__name__)


class HyDEGenerator:
    """HyDE 生成器"""

    # HyDE 提示模板
    HYDE_PROMPT = """你是一个企业知识库助手。根据用户的问题，生成一段可能包含答案的文档内容。

要求：
1. 生成的内容应该像是企业内部文档（制度、流程、手册等）
2. 包含与问题相关的关键信息
3. 使用正式的企业文档语言风格
4. 长度控制在 200-300 字

用户问题：{query}

请生成可能包含答案的文档内容："""

    def __init__(self):
        self.settings = get_settings()
        self._client = None

    def _get_client(self):
        """获取 LLM 客户端"""
        if self._client is not None:
            return self._client

        from openai import AsyncOpenAI
        import httpx

        if self.settings.LLM_PROVIDER == "cloud":
            api_key = self.settings.MIMO_API_KEY
            base_url = self.settings.MIMO_API_BASE
        else:
            api_key = "not-needed"
            base_url = f"http://localhost:{self.settings.LOCAL_MODEL_PORT}/v1"

        transport = httpx.AsyncHTTPTransport(proxy=None)
        http_client = httpx.AsyncClient(transport=transport, timeout=httpx.Timeout(30.0))

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=http_client,
        )

        return self._client

    async def generate(self, query: str) -> str:
        """
        生成假设性文档

        Args:
            query: 用户查询

        Returns:
            假设性文档内容
        """
        client = self._get_client()

        prompt = self.HYDE_PROMPT.format(query=query)

        try:
            response = await client.chat.completions.create(
                model=self.settings.MIMO_MODEL_NAME if self.settings.LLM_PROVIDER == "cloud" else self.settings.LOCAL_MODEL_NAME,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.warning(f"HyDE generation failed: {e}, using original query")
            return query

    async def generate_multi(self, query: str, num_hypotheses: int = 3) -> List[str]:
        """
        生成多个假设性文档

        Args:
            query: 用户查询
            num_hypotheses: 假设文档数量

        Returns:
            假设性文档列表
        """
        client = self._get_client()

        multi_prompt = f"""你是一个企业知识库助手。根据用户的问题，从不同角度生成 {num_hypotheses} 段可能包含答案的文档内容。

要求：
1. 每段内容从不同角度或场景描述
2. 使用正式的企业文档语言风格
3. 每段长度 100-200 字
4. 用 "---" 分隔每段内容

用户问题：{query}

请生成 {num_hypotheses} 段可能包含答案的文档内容："""

        try:
            response = await client.chat.completions.create(
                model=self.settings.MIMO_MODEL_NAME if self.settings.LLM_PROVIDER == "cloud" else self.settings.LOCAL_MODEL_NAME,
                messages=[
                    {"role": "user", "content": multi_prompt}
                ],
                max_tokens=1000,
                temperature=0.8,
            )

            content = response.choices[0].message.content.strip()
            hypotheses = [h.strip() for h in content.split("---") if h.strip()]

            return hypotheses[:num_hypotheses]

        except Exception as e:
            logger.warning(f"Multi-HyDE generation failed: {e}, using original query")
            return [query]


class HyDESearcher:
    """HyDE 检索器"""

    def __init__(self, hybrid_searcher, hyde_generator: Optional[HyDEGenerator] = None):
        self.hybrid_searcher = hybrid_searcher
        self.hyde_generator = hyde_generator or HyDEGenerator()

    async def search(
        self,
        query: str,
        top_k: int = 5,
        use_multi_hyde: bool = False,
        num_hypotheses: int = 3,
        filter_expr: Optional[str] = None,
    ):
        """
        HyDE 检索

        Args:
            query: 用户查询
            top_k: 返回数量
            use_multi_hyde: 是否使用多假设
            num_hypotheses: 假设数量
            filter_expr: 过滤表达式

        Returns:
            检索结果列表
        """
        from .vector_store import SearchResult

        if use_multi_hyde:
            # 多假设 HyDE
            hypotheses = await self.hyde_generator.generate_multi(query, num_hypotheses)

            # 对每个假设进行检索
            all_results = []
            for hypothesis in hypotheses:
                results = await self.hybrid_searcher.search(
                    hypothesis,
                    top_k=top_k,
                    filter_expr=filter_expr,
                )
                all_results.extend(results)

            # 去重并按分数排序
            seen = set()
            unique_results = []
            for r in all_results:
                if r.content not in seen:
                    seen.add(r.content)
                    unique_results.append(r)

            unique_results.sort(key=lambda x: x.score, reverse=True)
            return unique_results[:top_k]

        else:
            # 单假设 HyDE
            hypothesis = await self.hyde_generator.generate(query)

            # 用假设文档检索
            results = await self.hybrid_searcher.search(
                hypothesis,
                top_k=top_k,
                filter_expr=filter_expr,
            )

            # 补充：也用原始查询检索，合并结果
            original_results = await self.hybrid_searcher.search(
                query,
                top_k=top_k,
                filter_expr=filter_expr,
            )

            # 合并去重
            seen = set()
            combined = []
            for r in results + original_results:
                if r.content not in seen:
                    seen.add(r.content)
                    combined.append(r)

            combined.sort(key=lambda x: x.score, reverse=True)
            return combined[:top_k]


# 工厂函数
def get_hyde_searcher(hybrid_searcher) -> HyDESearcher:
    """获取 HyDE 检索器"""
    return HyDESearcher(
        hybrid_searcher=hybrid_searcher,
        hyde_generator=HyDEGenerator(),
    )
