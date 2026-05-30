from fastapi import APIRouter
from backend.auth.router import router as auth_router
from backend.chat.router import chat_router
from backend.evaluation.router import eval_router
from backend.knowledge.router import knowledge_router

api_router = APIRouter(prefix="/api/v1")

# 注册子路由
api_router.include_router(auth_router)
api_router.include_router(chat_router)
api_router.include_router(eval_router)
api_router.include_router(knowledge_router)


@api_router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "version": "1.0.0"}
