"""
RAGAS 评估模块
- Faithfulness: 回答是否基于检索内容
- Answer Relevancy: 回答是否与问题相关
- Context Precision: 检索内容的精确度
- Context Recall: 检索内容的召回率
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import logging
import json

from backend.config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class EvalCase:
    """评估用例"""
    question: str
    ground_truth: str  # 标准答案
    contexts: List[str] = field(default_factory=list)  # 检索到的上下文
    answer: str = ""  # 生成的回答


@dataclass
class RAGASResult:
    """RAGAS 评估结果"""
    faithfulness: float  # 忠实度：回答是否基于上下文
    answer_relevancy: float  # 相关性：回答是否与问题相关
    context_precision: float  # 精确度：上下文是否精确
    context_recall: float  # 召回率：上下文是否全面
    overall_score: float  # 综合分数

    def to_dict(self) -> Dict[str, float]:
        return {
            "faithfulness": self.faithfulness,
            "answer_relevancy": self.answer_relevancy,
            "context_precision": self.context_precision,
            "context_recall": self.context_recall,
            "overall_score": self.overall_score,
        }


class RAGASEvaluator:
    """RAGAS 评估器"""

    # Faithfulness 评估提示
    FAITHFULNESS_PROMPT = """请判断以下回答是否完全基于给定的上下文内容。

上下文：
{contexts}

问题：{question}

回答：{answer}

请评估：
1. 回答中的每个事实性陈述是否都能在上下文中找到依据
2. 是否存在上下文中没有提到的信息

请返回 JSON 格式：
{{"score": 0-1之间的分数, "reason": "评估原因"}}"""

    # Answer Relevancy 评估提示
    ANSWER_RELEVANCY_PROMPT = """请判断以下回答是否与问题相关。

问题：{question}

回答：{answer}

请评估：
1. 回答是否直接回应了问题
2. 回答是否包含了问题所需的信息
3. 回答是否有无关内容

请返回 JSON 格式：
{{"score": 0-1之间的分数, "reason": "评估原因"}}"""

    # Context Precision 评估提示
    CONTEXT_PRECISION_PROMPT = """请判断以下检索到的上下文是否精确相关。

问题：{question}

上下文：
{contexts}

请评估：
1. 每段上下文是否与问题相关
2. 是否包含无关信息
3. 信息密度如何

请返回 JSON 格式：
{{"score": 0-1之间的分数, "reason": "评估原因"}}"""

    # Context Recall 评估提示
    CONTEXT_RECALL_PROMPT = """请判断以下检索到的上下文是否全面覆盖了回答所需的信息。

标准答案：{ground_truth}

检索到的上下文：
{contexts}

请评估：
1. 上下文是否包含了回答问题所需的所有关键信息
2. 是否有重要信息缺失

请返回 JSON 格式：
{{"score": 0-1之间的分数, "reason": "评估原因"}}"""

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
        http_client = httpx.AsyncClient(transport=transport, timeout=httpx.Timeout(60.0))

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=http_client,
        )

        return self._client

    async def _llm_evaluate(self, prompt: str) -> Dict[str, Any]:
        """使用 LLM 进行评估"""
        client = self._get_client()

        try:
            response = await client.chat.completions.create(
                model=self.settings.MIMO_MODEL_NAME if self.settings.LLM_PROVIDER == "cloud" else self.settings.LOCAL_MODEL_NAME,
                messages=[
                    {"role": "system", "content": "你是一个评估专家，请客观评估并返回 JSON 格式结果。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1,  # 低温度保证一致性
            )

            content = response.choices[0].message.content.strip()

            # 解析 JSON
            # 尝试提取 JSON
            if "{" in content:
                json_str = content[content.index("{"):content.rindex("}") + 1]
                return json.loads(json_str)

            return {"score": 0.5, "reason": "无法解析评估结果"}

        except Exception as e:
            logger.warning(f"LLM evaluation failed: {e}")
            return {"score": 0.5, "reason": f"评估失败: {str(e)}"}

    async def evaluate_faithfulness(self, case: EvalCase) -> float:
        """评估忠实度"""
        contexts_str = "\n".join([f"[{i+1}] {ctx}" for i, ctx in enumerate(case.contexts)])

        prompt = self.FAITHFULNESS_PROMPT.format(
            contexts=contexts_str,
            question=case.question,
            answer=case.answer,
        )

        result = await self._llm_evaluate(prompt)
        return result.get("score", 0.5)

    async def evaluate_answer_relevancy(self, case: EvalCase) -> float:
        """评估回答相关性"""
        prompt = self.ANSWER_RELEVANCY_PROMPT.format(
            question=case.question,
            answer=case.answer,
        )

        result = await self._llm_evaluate(prompt)
        return result.get("score", 0.5)

    async def evaluate_context_precision(self, case: EvalCase) -> float:
        """评估上下文精确度"""
        contexts_str = "\n".join([f"[{i+1}] {ctx}" for i, ctx in enumerate(case.contexts)])

        prompt = self.CONTEXT_PRECISION_PROMPT.format(
            question=case.question,
            contexts=contexts_str,
        )

        result = await self._llm_evaluate(prompt)
        return result.get("score", 0.5)

    async def evaluate_context_recall(self, case: EvalCase) -> float:
        """评估上下文召回率"""
        contexts_str = "\n".join([f"[{i+1}] {ctx}" for i, ctx in enumerate(case.contexts)])

        prompt = self.CONTEXT_RECALL_PROMPT.format(
            ground_truth=case.ground_truth,
            contexts=contexts_str,
        )

        result = await self._llm_evaluate(prompt)
        return result.get("score", 0.5)

    async def evaluate(self, case: EvalCase) -> RAGASResult:
        """
        完整 RAGAS 评估

        Args:
            case: 评估用例

        Returns:
            RAGAS 评估结果
        """
        # 并行评估各指标
        import asyncio

        faithfulness, answer_relevancy, context_precision, context_recall = await asyncio.gather(
            self.evaluate_faithfulness(case),
            self.evaluate_answer_relevancy(case),
            self.evaluate_context_precision(case),
            self.evaluate_context_recall(case),
        )

        # 计算综合分数（加权平均）
        overall_score = (
            faithfulness * 0.3 +
            answer_relevancy * 0.3 +
            context_precision * 0.2 +
            context_recall * 0.2
        )

        return RAGASResult(
            faithfulness=faithfulness,
            answer_relevancy=answer_relevancy,
            context_precision=context_precision,
            context_recall=context_recall,
            overall_score=overall_score,
        )

    async def evaluate_batch(self, cases: List[EvalCase]) -> Dict[str, Any]:
        """
        批量评估

        Args:
            cases: 评估用例列表

        Returns:
            评估报告
        """
        results = []
        for case in cases:
            result = await self.evaluate(case)
            results.append(result)

        # 计算平均分数
        avg_faithfulness = sum(r.faithfulness for r in results) / len(results)
        avg_answer_relevancy = sum(r.answer_relevancy for r in results) / len(results)
        avg_context_precision = sum(r.context_precision for r in results) / len(results)
        avg_context_recall = sum(r.context_recall for r in results) / len(results)
        avg_overall = sum(r.overall_score for r in results) / len(results)

        return {
            "total_cases": len(cases),
            "average_scores": {
                "faithfulness": avg_faithfulness,
                "answer_relevancy": avg_answer_relevancy,
                "context_precision": avg_context_precision,
                "context_recall": avg_context_recall,
                "overall_score": avg_overall,
            },
            "individual_results": [r.to_dict() for r in results],
            "passed": avg_overall >= self.settings.RAGAS_FAITHFULNESS_THRESHOLD,
        }


# 单例
_evaluator: Optional[RAGASEvaluator] = None


def get_ragas_evaluator() -> RAGASEvaluator:
    """获取 RAGAS 评估器单例"""
    global _evaluator
    if _evaluator is None:
        _evaluator = RAGASEvaluator()
    return _evaluator
