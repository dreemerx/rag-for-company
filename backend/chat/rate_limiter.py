import time
import threading
from typing import Dict, Optional
from collections import defaultdict
from fastapi import HTTPException, status

from backend.config.settings import get_settings


class RateLimiter:
    """
    限流器
    - 单用户每分钟最多 N 次请求
    - 单次对话 Token 上限
    """

    def __init__(self):
        settings = get_settings()
        self.max_requests_per_minute = settings.RATE_LIMIT_PER_MINUTE
        self.max_tokens_per_session = settings.TOKEN_LIMIT_PER_SESSION

        # 存储用户请求记录: {user_id: [(timestamp, tokens_used), ...]}
        self._request_log: Dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()

    def check_rate_limit(self, user_id: str) -> bool:
        """检查用户是否超过请求频率限制"""
        now = time.time()
        minute_ago = now - 60

        with self._lock:
            # 清理过期记录
            self._request_log[user_id] = [
                (ts, tokens) for ts, tokens in self._request_log[user_id]
                if ts > minute_ago
            ]

            # 检查请求数量
            if len(self._request_log[user_id]) >= self.max_requests_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"请求过于频繁，每分钟最多 {self.max_requests_per_minute} 次请求"
                )

        return True

    def check_token_limit(self, user_id: str, tokens_used: int) -> bool:
        """检查用户是否超过 Token 使用限制"""
        with self._lock:
            # 计算当前会话已使用的 Token
            total_tokens = sum(
                tokens for _, tokens in self._request_log[user_id]
            )

            if total_tokens + tokens_used > self.max_tokens_per_session:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"本次会话 Token 使用已达上限（{self.max_tokens_per_session}）"
                )

        return True

    def record_request(self, user_id: str, tokens_used: int = 0) -> None:
        """记录用户请求"""
        with self._lock:
            self._request_log[user_id].append((time.time(), tokens_used))

    def get_remaining_quota(self, user_id: str) -> dict:
        """获取用户剩余配额"""
        now = time.time()
        minute_ago = now - 60

        with self._lock:
            # 清理过期记录
            self._request_log[user_id] = [
                (ts, tokens) for ts, tokens in self._request_log[user_id]
                if ts > minute_ago
            ]

            requests_made = len(self._request_log[user_id])
            tokens_used = sum(tokens for _, tokens in self._request_log[user_id])

        return {
            "remaining_requests": max(0, self.max_requests_per_minute - requests_made),
            "remaining_tokens": max(0, self.max_tokens_per_session - tokens_used),
            "max_requests_per_minute": self.max_requests_per_minute,
            "max_tokens_per_session": self.max_tokens_per_session,
        }

    def reset_user(self, user_id: str) -> None:
        """重置用户限制记录"""
        with self._lock:
            if user_id in self._request_log:
                del self._request_log[user_id]


# 单例（线程安全）
_rate_limiter: Optional[RateLimiter] = None
_rate_limiter_lock = threading.Lock()


def get_rate_limiter() -> RateLimiter:
    """获取限流器单例"""
    global _rate_limiter
    if _rate_limiter is None:
        with _rate_limiter_lock:
            if _rate_limiter is None:
                _rate_limiter = RateLimiter()
    return _rate_limiter
