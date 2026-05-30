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

    # 向量数据库
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    CHROMA_COLLECTION_NAME: str = "company_knowledge"

    # JWT 认证
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 数据库
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/app.db"

    # 限流配置
    RATE_LIMIT_PER_MINUTE: int = 20
    TOKEN_LIMIT_PER_SESSION: int = 50000

    # 知识库
    KNOWLEDGE_BASE_DIR: str = "./data/knowledge_base"

    # 评测
    EVAL_ACCURACY_THRESHOLD: float = 0.85

    # 服务配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """获取全局配置单例"""
    return Settings()
