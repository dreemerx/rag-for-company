import logging
import json
import os
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler


class JSONFormatter(logging.Formatter):
    """JSON 格式化器，用于文件日志"""

    def format(self, record):
        log = {
            "time": datetime.now().isoformat(),
            "level": record.levelname,
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log["exception"] = self.formatException(record.exc_info)
        # 附加额外字段（如 user_id, request_id 等）
        if hasattr(record, "extra_data"):
            log["data"] = record.extra_data
        return json.dumps(log, ensure_ascii=False)


class ReadableFormatter(logging.Formatter):
    """人类可读格式化器，用于控制台输出"""

    def format(self, record):
        time_str = datetime.now().strftime("%H:%M:%S")
        level = record.levelname.ljust(8)
        msg = record.getMessage()
        result = f"[{time_str}] {level} {record.module}:{record.lineno} - {msg}"
        if record.exc_info:
            result += "\n" + self.formatException(record.exc_info)
        return result


def setup_logging(log_dir: str = "data/logs", log_level: str = "INFO"):
    """
    初始化日志系统

    Args:
        log_dir: 日志文件目录
        log_level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
    """
    os.makedirs(log_dir, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # 清除已有的 handler（避免重复）
    root_logger.handlers.clear()

    # 控制台 handler — 人类可读
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ReadableFormatter())
    console_handler.setLevel(logging.DEBUG)
    root_logger.handlers.append(console_handler)

    # 文件 handler — JSON 格式，按天轮转，保留 30 天
    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(log_dir, "app.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setFormatter(JSONFormatter())
    file_handler.setLevel(logging.INFO)
    root_logger.handlers.append(file_handler)

    # 错误单独文件
    error_handler = TimedRotatingFileHandler(
        filename=os.path.join(log_dir, "error.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    error_handler.setFormatter(JSONFormatter())
    error_handler.setLevel(logging.ERROR)
    root_logger.handlers.append(error_handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的 logger"""
    return logging.getLogger(name)
