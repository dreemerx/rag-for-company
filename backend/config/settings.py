import secrets
import warnings
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # LLM 配置
    LLM_PROVIDER: str = "cloud"

    # 云端 LLM (MiMo)
    MIMO_API_KEY: str = ""
    MIMO_API_BASE: str = "https://api.mimo.com/v1"
    MIMO_MODEL_NAME: str = "mimo-chat"

    # 本地 LLM (Qwen)
    LOCAL_MODEL_PATH: str = "/models/qwen"
    LOCAL_MODEL_PORT: int = 8000
    LOCAL_MODEL_NAME: str = "qwen-chat"

    # Milvus 向量数据库
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION_NAME: str = "company_knowledge"
    MILVUS_DIMENSION: int = 512  # bge-small-zh-v1.5 输出维度

    # Embedding 模型
    EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"  # 与 MILVUS_DIMENSION=512 匹配
    EMBEDDING_DEVICE: str = "cpu"  # cpu 或 cuda

    # Reranker 模型
    RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"
    RERANKER_TOP_K: int = 5

    # 分块配置
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    # Hybrid Search 配置
    BM25_WEIGHT: float = 0.3
    VECTOR_WEIGHT: float = 0.7

    # JWT 认证
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 数据库
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/app.db"

    # 限流配置
    RATE_LIMIT_PER_MINUTE: int = 20
    TOKEN_LIMIT_PER_SESSION: int = 50000

    # 记忆管理
    HISTORY_WINDOW_SIZE: int = 10          # 滑动窗口大小（保留最近 N 条消息）
    SUMMARY_TRIGGER_COUNT: int = 20        # 触发摘要的消息数阈值

    # 知识库
    KNOWLEDGE_BASE_DIR: str = "./data/knowledge_base"

    # 评测
    EVAL_ACCURACY_THRESHOLD: float = 0.85

    # RAGAS 评估
    RAGAS_FAITHFULNESS_THRESHOLD: float = 0.7
    RAGAS_RELEVANCE_THRESHOLD: float = 0.7

    # 服务配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "data/logs"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def _validate_settings(settings: Settings) -> Settings:
    """验证配置安全性"""
    # 如果未设置 JWT 密钥，自动生成并警告
    if not settings.JWT_SECRET_KEY or settings.JWT_SECRET_KEY == "your-secret-key-change-in-production":
        generated_key = secrets.token_urlsafe(32)
        warnings.warn(
            "JWT_SECRET_KEY 未设置或使用了默认值！已自动生成临时密钥。"
            "请在 .env 文件中设置 JWT_SECRET_KEY 以确保生产安全。",
            UserWarning,
            stacklevel=2,
        )
        settings.JWT_SECRET_KEY = generated_key
    return settings


@lru_cache()
def get_settings() -> Settings:
    """获取全局配置单例"""
    settings = Settings()
    return _validate_settings(settings)
