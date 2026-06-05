"""
API 路由聚合模块
- 统一前缀 /api/v1
- 聚合认证、对话、评测、知识库四个子路由
- 提供健康检查和监控指标端点
"""
from fastapi import APIRouter
from backend.auth.router import router as auth_router
from backend.chat.router import chat_router
from backend.evaluation.router import eval_router
from backend.knowledge.router import knowledge_router
from backend.utils import metrics

# 创建带统一前缀的路由
api_router = APIRouter(prefix="/api/v1")

# 注册子路由
api_router.include_router(auth_router)        # 认证路由（/auth/*）
api_router.include_router(chat_router)        # 对话路由（/chat/*）
api_router.include_router(eval_router)        # 评测路由（/evaluation/*）
api_router.include_router(knowledge_router)   # 知识库路由（/knowledge/*）


@api_router.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "version": "1.0.0"}


@api_router.get("/metrics")
async def get_metrics():
    """监控指标端点"""
    return metrics.get_snapshot()
