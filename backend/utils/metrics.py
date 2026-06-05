import time
import threading
from collections import defaultdict
from datetime import datetime


class Metrics:
    """内存中的监控指标统计（线程安全）"""

    def __init__(self):
        self._lock = threading.Lock()
        self._start_time = time.time()

        # 计数器
        self.request_count = 0
        self.error_count = 0
        self.llm_call_count = 0
        self.llm_error_count = 0
        self.llm_total_tokens = 0
        self.llm_prompt_tokens = 0
        self.llm_completion_tokens = 0

        # 工具调用统计 {tool_name: {"count": N, "errors": N, "total_time": float}}
        self.tool_stats = defaultdict(lambda: {"count": 0, "errors": 0, "total_time": 0.0})

        # 响应时间（最近 100 个请求）
        self._response_times = []
        self._max_samples = 100

        # 错误时间戳（用于告警判断）
        self._recent_errors = []

    def record_request(self, method: str, path: str, status_code: int, duration: float):
        """记录一次 HTTP 请求"""
        with self._lock:
            self.request_count += 1
            self._response_times.append(duration)
            if len(self._response_times) > self._max_samples:
                self._response_times.pop(0)
            if status_code >= 400:
                self.error_count += 1

    def record_llm_call(self, prompt_tokens: int = 0, completion_tokens: int = 0, success: bool = True):
        """记录一次 LLM 调用"""
        with self._lock:
            self.llm_call_count += 1
            self.llm_prompt_tokens += prompt_tokens
            self.llm_completion_tokens += completion_tokens
            self.llm_total_tokens += prompt_tokens + completion_tokens
            if not success:
                self.llm_error_count += 1
                self._recent_errors.append(time.time())

    def record_tool_call(self, tool_name: str, duration: float, success: bool = True):
        """记录一次工具调用"""
        with self._lock:
            self.tool_stats[tool_name]["count"] += 1
            self.tool_stats[tool_name]["total_time"] += duration
            if not success:
                self.tool_stats[tool_name]["errors"] += 1
                self._recent_errors.append(time.time())

    def get_snapshot(self) -> dict:
        """获取当前指标快照"""
        with self._lock:
            uptime = time.time() - self._start_time
            avg_response = (
                sum(self._response_times) / len(self._response_times)
                if self._response_times
                else 0
            )

            tool_summary = {}
            for name, stats in self.tool_stats.items():
                tool_summary[name] = {
                    "count": stats["count"],
                    "errors": stats["errors"],
                    "avg_time": round(stats["total_time"] / stats["count"], 3) if stats["count"] > 0 else 0,
                    "error_rate": round(stats["errors"] / stats["count"] * 100, 1) if stats["count"] > 0 else 0,
                }

            return {
                "uptime_seconds": round(uptime),
                "requests": {
                    "total": self.request_count,
                    "errors": self.error_count,
                    "error_rate": round(self.error_count / self.request_count * 100, 1) if self.request_count > 0 else 0,
                },
                "llm": {
                    "calls": self.llm_call_count,
                    "errors": self.llm_error_count,
                    "total_tokens": self.llm_total_tokens,
                    "prompt_tokens": self.llm_prompt_tokens,
                    "completion_tokens": self.llm_completion_tokens,
                },
                "tools": tool_summary,
                "performance": {
                    "avg_response_time_ms": round(avg_response * 1000, 1),
                    "sample_size": len(self._response_times),
                },
                "snapshot_time": datetime.now().isoformat(),
            }

    def get_recent_error_count(self, seconds: int = 60) -> int:
        """获取最近 N 秒内的错误数"""
        cutoff = time.time() - seconds
        with self._lock:
            self._recent_errors = [t for t in self._recent_errors if t > cutoff]
            return len(self._recent_errors)


# 全局单例
metrics = Metrics()
