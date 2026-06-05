"""
评测运行器
- 支持传统关键词匹配评测
- 支持 RAGAS 多维度评测
"""
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import logging
import time

from .dataset import EvaluationDataset, EvalCase
from backend.agent.core import get_agent
from backend.config.settings import get_settings
from .ragas_eval import get_ragas_evaluator, RAGASEvaluator, RAGASResult

logger = logging.getLogger(__name__)


@dataclass
class EvalResult:
    """单条评测结果"""
    case_id: str
    question: str
    expected: str
    actual: str
    passed: bool
    category: str
    contexts: List[str] = field(default_factory=list)
    ragas: Optional[RAGASResult] = None


@dataclass
class EvalReport:
    """评测报告"""
    total: int
    passed: int
    failed: int
    accuracy: float
    results: List[EvalResult]
    category_accuracy: Dict[str, float]
    ragas_scores: Optional[Dict[str, float]] = None


class EvaluationRunner:
    """评测运行器"""

    def __init__(self, use_ragas: bool = False):
        self.dataset = EvaluationDataset()
        self.agent = get_agent()
        self.use_ragas = use_ragas
        self.ragas_evaluator = get_ragas_evaluator() if use_ragas else None

    async def run(
        self,
        user_id: str = "eval_user",
        user_name: str = "评测用户",
        department: str = "技术部",
        role: str = "user",
        category: str = None,
    ) -> EvalReport:
        """运行评测"""
        cases = self.dataset.get_cases(category)
        results: List[EvalResult] = []

        for case in cases:
            # 获取检索上下文
            contexts = await self._get_contexts(case.question)

            # 调用 Agent
            actual = await self.agent.chat(
                user_id=user_id,
                user_name=user_name,
                department=department,
                role=role,
                message=case.question,
            )

            # 传统关键词匹配
            passed = case.expected_answer.lower() in actual.lower()

            # RAGAS 评估
            ragas_result = None
            if self.use_ragas and self.ragas_evaluator:
                from .ragas_eval import EvalCase as RAGASEvalCase
                ragas_case = RAGASEvalCase(
                    question=case.question,
                    ground_truth=case.expected_answer,
                    contexts=contexts,
                    answer=actual,
                )
                ragas_result = await self.ragas_evaluator.evaluate(ragas_case)

                # 如果 RAGAS 分数高，认为通过
                if ragas_result.overall_score >= 0.7:
                    passed = True

            results.append(EvalResult(
                case_id=case.id,
                question=case.question,
                expected=case.expected_answer,
                actual=actual[:500],  # 截断过长的回复
                passed=passed,
                category=case.category,
                contexts=contexts,
                ragas=ragas_result,
            ))

        # 计算统计
        passed_count = sum(1 for r in results if r.passed)
        total = len(results)
        accuracy = passed_count / total if total > 0 else 0.0

        # 按类别统计
        category_stats: Dict[str, List[bool]] = {}
        for r in results:
            if r.category not in category_stats:
                category_stats[r.category] = []
            category_stats[r.category].append(r.passed)

        category_accuracy = {
            cat: sum(passes) / len(passes)
            for cat, passes in category_stats.items()
        }

        # RAGAS 平均分数
        ragas_scores = None
        if self.use_ragas:
            ragas_results = [r.ragas for r in results if r.ragas is not None]
            if ragas_results:
                ragas_scores = {
                    "faithfulness": sum(r.faithfulness for r in ragas_results) / len(ragas_results),
                    "answer_relevancy": sum(r.answer_relevancy for r in ragas_results) / len(ragas_results),
                    "context_precision": sum(r.context_precision for r in ragas_results) / len(ragas_results),
                    "context_recall": sum(r.context_recall for r in ragas_results) / len(ragas_results),
                    "overall_score": sum(r.overall_score for r in ragas_results) / len(ragas_results),
                }

        return EvalReport(
            total=total,
            passed=passed_count,
            failed=total - passed_count,
            accuracy=accuracy,
            results=results,
            category_accuracy=category_accuracy,
            ragas_scores=ragas_scores,
        )

    async def _get_contexts(self, question: str) -> List[str]:
        """获取检索上下文"""
        try:
            from backend.knowledge.rag_pipeline import get_rag_pipeline
            pipeline = get_rag_pipeline()
            results = await pipeline.search(question, top_k=5)
            return [r.content for r in results]
        except Exception as e:
            logger.warning(f"Failed to get contexts: {e}")
            return []

    async def check_threshold(self) -> bool:
        """检查是否达到准确率阈值"""
        settings = get_settings()
        report = await self.run()
        return report.accuracy >= settings.EVAL_ACCURACY_THRESHOLD
