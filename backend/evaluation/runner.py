from typing import List, Dict
from dataclasses import dataclass

from .dataset import EvaluationDataset, EvalCase
from backend.agent.core import get_agent
from backend.config.settings import get_settings


@dataclass
class EvalResult:
    """单条评测结果"""
    case_id: str
    question: str
    expected: str
    actual: str
    passed: bool
    category: str


@dataclass
class EvalReport:
    """评测报告"""
    total: int
    passed: int
    failed: int
    accuracy: float
    results: List[EvalResult]
    category_accuracy: Dict[str, float]


class EvaluationRunner:
    """评测运行器"""

    def __init__(self):
        self.dataset = EvaluationDataset()
        self.agent = get_agent()

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
            # 调用 Agent
            actual = await self.agent.chat(
                user_id=user_id,
                user_name=user_name,
                department=department,
                role=role,
                message=case.question,
            )

            # 检查是否包含预期答案
            passed = case.expected_answer.lower() in actual.lower()

            results.append(EvalResult(
                case_id=case.id,
                question=case.question,
                expected=case.expected_answer,
                actual=actual[:200],  # 截断过长的回复
                passed=passed,
                category=case.category,
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

        return EvalReport(
            total=total,
            passed=passed_count,
            failed=total - passed_count,
            accuracy=accuracy,
            results=results,
            category_accuracy=category_accuracy,
        )

    async def check_threshold(self) -> bool:
        """检查是否达到准确率阈值"""
        settings = get_settings()
        report = await self.run()
        return report.accuracy >= settings.EVAL_ACCURACY_THRESHOLD
