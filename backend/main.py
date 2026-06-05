import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.router import api_router
from backend.database import init_db, close_db
from backend.config.settings import get_settings
from backend.utils import setup_logging, metrics, alert_manager
from backend.utils.middleware import RequestLoggingMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    settings = get_settings()

    # 初始化日志系统
    setup_logging(log_dir=settings.LOG_DIR, log_level=settings.LOG_LEVEL)
    logger.info("日志系统初始化完成")

    # 创建数据目录
    os.makedirs(settings.KNOWLEDGE_BASE_DIR, exist_ok=True)

    await init_db()
    logger.info("数据库初始化完成")

    # 预加载 Embedding 和 Reranker 模型
    try:
        from backend.knowledge.embedding import get_embedding_manager
        from backend.knowledge.reranker import get_reranker
        get_embedding_manager()
        logger.info("Embedding 模型加载完成")
        get_reranker()
        logger.info("Reranker 模型加载完成")
    except Exception as e:
        logger.warning(f"模型预加载失败（首次使用时会自动加载）: {e}")

    yield

    # 关闭时清理
    from backend.knowledge.vector_store import get_vector_store
    try:
        await get_vector_store().close()
    except Exception as e:
        logger.warning(f"关闭向量数据库连接失败: {e}")

    await close_db()
    logger.info("应用已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="企业 RAG 智能助手",
    description="面向企业内部员工的 RAG 智能代理系统",
    version="1.0.0",
    lifespan=lifespan,
)

# 中间件（注意：后注册的先执行）
app.add_middleware(RequestLoggingMiddleware)  # 请求日志
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# 注册路由
app.include_router(api_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.exception(f"{request.method} {request.url}: {exc}")
    alert_manager.check_unhandled_exception("global", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请联系管理员"},
    )


@app.get("/")
async def root():
    return {
        "name": "企业 RAG 智能助手",
        "version": "1.0.0",
        "docs": "/docs",
    }




if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
