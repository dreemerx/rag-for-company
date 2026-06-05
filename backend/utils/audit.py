import logging
import json
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

_audit_logger = None


def _get_audit_logger() -> logging.Logger:
    """获取审计日志 logger（单例）"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = logging.getLogger("audit")
        _audit_logger.setLevel(logging.INFO)
        _audit_logger.propagate = False  # 不传递到 root logger

        log_dir = "data/logs"
        os.makedirs(log_dir, exist_ok=True)

        handler = TimedRotatingFileHandler(
            filename=os.path.join(log_dir, "audit.log"),
            when="midnight",
            interval=1,
            backupCount=90,  # 审计日志保留 90 天
            encoding="utf-8",
        )

        class AuditFormatter(logging.Formatter):
            def format(self, record):
                return record.getMessage()

        handler.setFormatter(AuditFormatter())
        _audit_logger.handlers.append(handler)

    return _audit_logger


def audit_log(event: str, user_id: int = None, username: str = None, **kwargs):
    """
    记录审计日志

    Args:
        event: 事件类型 (login/register/chat/tool_call/upload/denied)
        user_id: 用户 ID
        username: 用户名
        **kwargs: 其他需要记录的字段
    """
    logger = _get_audit_logger()

    entry = {
        "time": datetime.now().isoformat(),
        "event": event,
    }
    if user_id is not None:
        entry["user_id"] = user_id
    if username is not None:
        entry["username"] = username
    entry.update(kwargs)

    logger.info(json.dumps(entry, ensure_ascii=False))
