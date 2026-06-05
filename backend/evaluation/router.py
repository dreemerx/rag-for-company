"""
评测 API 路由
- 运行评测
- RAGAS 评测
- 检查评测状态
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict

from backend.auth.models import User
from backend.auth.rbac import require_role
from .runner import EvaluationRunner

eval_router = APIRouter(prefix="/evaluation", tags=["评测"])


class EvalRequest(BaseModel):
    category: Optional[str] = None
    use_ragas: bool = False


class EvalResponse(BaseModel):
    total: int
    passed: int
    failed: int
    accuracy: float
    category_accuracy: dict
    ragas_scores: Optional[dict] = None


@eval_router.post("/run", response_model=EvalResponse)
async def run_evaluation(
    request: EvalRequest = EvalRequest(),
    current_user: User = Depends(require_role("admin")),
):
    """运行评测（仅管理员）"""
    runner = EvaluationRunner(use_ragas=request.use_ragas)
    report = await runner.run(category=request.category)

    return EvalResponse(
        total=report.total,
        passed=report.passed,
        failed=report.failed,
        accuracy=report.accuracy,
        category_accuracy=report.category_accuracy,
        ragas_scores=report.ragas_scores,
    )


@eval_router.get("/check")
async def check_evaluation(current_user: User = Depends(require_role("admin"))):
    """检查评测是否达标"""
    runner = EvaluationRunner()
    passed = await runner.check_threshold()
    return {
        "passed": passed,
        "message": "评测通过" if passed else "评测未达标准",
    }


@eval_router.post("/ragas")
async def run_ragas_evaluation(
    request: EvalRequest = EvalRequest(),
    current_user: User = Depends(require_role("admin")),
):
    """运行 RAGAS 评测（仅管理员）"""
    runner = EvaluationRunner(use_ragas=True)
    report = await runner.run(category=request.category)

    return {
        "total": report.total,
        "passed": report.passed,
        "failed": report.failed,
        "accuracy": report.accuracy,
        "ragas_scores": report.ragas_scores,
        "details": [
            {
                "case_id": r.case_id,
                "question": r.question,
                "passed": r.passed,
                "ragas": r.ragas.to_dict() if r.ragas else None,
            }
            for r in report.results
        ],
    }
