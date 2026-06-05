import logging
import json
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from .metrics import metrics

_alert_logger = None


def _get_alert_logger() -> logging.Logger:
    """获取告警日志 logger（单例）"""
    global _alert_logger
    if _alert_logger is None:
        _alert_logger = logging.getLogger("alert")
        _alert_logger.setLevel(logging.WARNING)
        _alert_logger.propagate = False

        log_dir = "data/logs"
        os.makedirs(log_dir, exist_ok=True)

        handler = TimedRotatingFileHandler(
            filename=os.path.join(log_dir, "alert.log"),
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        )

        class AlertFormatter(logging.Formatter):
            def format(self, record):
                return record.getMessage()

        handler.setFormatter(AlertFormatter())
        _alert_logger.handlers.append(handler)

    return _alert_logger


class AlertManager:
    """告警管理器"""

    def __init__(self):
        self._llm_consecutive_errors = 0
        self._last_alert_time = {}  # 防止重复告警

    def check_llm_call(self, success: bool):
        """检查 LLM 调用，连续失败 3 次触发告警"""
        if success:
            self._llm_consecutive_errors = 0
        else:
            self._llm_consecutive_errors += 1
            if self._llm_consecutive_errors >= 3:
                self._fire_alert(
                    level="CRITICAL",
                    event="LLM 连续失败",
                    detail=f"连续失败 {self._llm_consecutive_errors} 次",
                    throttle_key="llm_consecutive_failures",
                    throttle_seconds=300,
                )

    def check_tool_call(self, tool_name: str, success: bool):
        """检查工具调用失败率"""
        stats = metrics.tool_stats.get(tool_name)
        if stats and stats["count"] >= 5:
            error_rate = stats["errors"] / stats["count"]
            if error_rate > 0.5:
                self._fire_alert(
                    level="WARNING",
                    event="工具调用失败率过高",
                    detail=f"工具 {tool_name} 失败率 {error_rate:.0%}",
                    throttle_key=f"tool_high_error_{tool_name}",
                    throttle_seconds=600,
                )

    def check_unhandled_exception(self, module: str, error: Exception):
        """未处理异常告警"""
        self._fire_alert(
            level="ERROR",
            event="未处理异常",
            detail=f"[{module}] {type(error).__name__}: {error}",
            throttle_key=f"unhandled_{module}",
            throttle_seconds=60,
        )

    def check_rate_limit(self, user_id: int):
        """频率限制告警"""
        self._fire_alert(
            level="WARNING",
            event="用户请求过于频繁",
            detail=f"user_id={user_id}",
            throttle_key=f"rate_limit_{user_id}",
            throttle_seconds=60,
        )

    def _fire_alert(self, level: str, event: str, detail: str, throttle_key: str = None, throttle_seconds: int = 60):
        """触发告警（带防抖）"""
        now = time.time()
        if throttle_key:
            last = self._last_alert_time.get(throttle_key, 0)
            if now - last < throttle_seconds:
                return
            self._last_alert_time[throttle_key] = now

        logger = _get_alert_logger()

        entry = {
            "time": datetime.now().isoformat(),
            "level": level,
            "event": event,
            "detail": detail,
        }

        log_level = getattr(logging, level, logging.ERROR)
        logger.log(log_level, json.dumps(entry, ensure_ascii=False))

        # 控制台也输出告警
        print(f"\n[ALERT] [{level}] {event}: {detail}\n")


import time  # 放在这里避免循环导入

# 全局单例
alert_manager = AlertManager()
