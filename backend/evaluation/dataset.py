"""
评测数据集管理模块
- 管理评测用例的加载、保存、添加
- 支持按类别筛选评测用例
- 自动生成默认数据集（覆盖所有工具类别）
"""
import json
from typing import List, Optional
from pathlib import Path
from dataclasses import dataclass


@dataclass
class EvalCase:
    """
    评测用例数据类

    Attributes:
        id: 用例 ID
        question: 测试问题
        expected_answer: 期望答案（用于关键词匹配）
        category: 类别（knowledge_base/database_query/ticket_manager/email_summary/approval_query）
        difficulty: 难度（easy/medium/hard）
    """
    id: str
    question: str
    expected_answer: str
    category: str
    difficulty: str


class EvaluationDataset:
    """评测数据集管理类"""

    def __init__(self, dataset_path: str = "tests/evaluation_dataset.json"):
        """
        初始化评测数据集

        Args:
            dataset_path: 数据集文件路径
        """
        self.dataset_path = Path(dataset_path)
        self.cases: List[EvalCase] = []
        self._load_dataset()

    def _load_dataset(self):
        """加载评测数据集，若文件不存在则创建默认数据集"""
        if not self.dataset_path.exists():
            self._create_default_dataset()
            return

        with open(self.dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.cases = [
            EvalCase(**case) for case in data.get("cases", [])
        ]

    def _create_default_dataset(self):
        """创建默认评测数据集，覆盖所有工具类别"""
        default_cases = [
            {
                "id": "eval_001",
                "question": "公司的年假政策是什么？",
                "expected_answer": "年假",
                "category": "knowledge_base",
                "difficulty": "easy",
            },
            {
                "id": "eval_002",
                "question": "本月销售数据是多少？",
                "expected_answer": "销售",
                "category": "database_query",
                "difficulty": "easy",
            },
            {
                "id": "eval_003",
                "question": "我有哪些待处理的工单？",
                "expected_answer": "工单",
                "category": "ticket_manager",
                "difficulty": "easy",
            },
            {
                "id": "eval_004",
                "question": "查看我的未读邮件",
                "expected_answer": "邮件",
                "category": "email_summary",
                "difficulty": "easy",
            },
            {
                "id": "eval_005",
                "question": "我的审批状态如何？",
                "expected_answer": "审批",
                "category": "approval_query",
                "difficulty": "easy",
            },
        ]

        # 保存到文件
        dataset = {"cases": default_cases}
        self.dataset_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.dataset_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)

        self.cases = [EvalCase(**case) for case in default_cases]

    def get_cases(self, category: Optional[str] = None) -> List[EvalCase]:
        """
        获取评测用例

        Args:
            category: 类别筛选（可选）

        Returns:
            评测用例列表
        """
        if category:
            return [c for c in self.cases if c.category == category]
        return self.cases

    def add_case(self, case: EvalCase) -> None:
        """
        添加评测用例并保存

        Args:
            case: 评测用例
        """
        self.cases.append(case)
        self._save_dataset()

    def _save_dataset(self):
        """保存数据集到文件"""
        data = {
            "cases": [
                {
                    "id": c.id,
                    "question": c.question,
                    "expected_answer": c.expected_answer,
                    "category": c.category,
                    "difficulty": c.difficulty,
                }
                for c in self.cases
            ]
        }
        with open(self.dataset_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
