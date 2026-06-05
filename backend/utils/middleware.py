import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件 — 记录每个请求的方法、路径、状态码、耗时"""

    async def dispatch(self, request: Request, call_next):
        start = time.time()

        # 跳过健康检查和 metrics 接口的日志，避免刷屏
        path = request.url.path
        if path in ("/api/v1/health", "/api/v1/metrics"):
            return await call_next(request)

        response = await call_next(request)
        duration = time.time() - start

        # 从 request.state 获取用户信息（如果认证中间件设置了的话）
        user_id = getattr(request.state, "user_id", None)

        logger.info(
            f"{request.method} {path} → {response.status_code} ({duration:.3f}s)"
            + (f" [user={user_id}]" if user_id else ""),
            extra={"extra_data": {
                "method": request.method,
                "path": path,
                "status": response.status_code,
                "duration": round(duration, 3),
                "user_id": user_id,
                "client_ip": request.client.host if request.client else None,
            }},
        )

        # 更新 metrics（延迟导入避免循环）
        from .metrics import metrics
        metrics.record_request(
            method=request.method,
            path=path,
            status_code=response.status_code,
            duration=duration,
        )

        return response
