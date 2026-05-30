from dataclasses import dataclass
from functools import lru_cache
from .settings import get_settings


@dataclass
class LLMConfig:
    """LLM 配置封装"""
    provider: str          # cloud 或 local
    api_key: str
    api_base: str
    model_name: str
    max_tokens: int = 4096
    temperature: float = 0.7


@lru_cache()
def get_llm_config() -> LLMConfig:
    """根据当前设置获取 LLM 配置"""
    settings = get_settings()

    if settings.LLM_PROVIDER == "cloud":
        return LLMConfig(
            provider="cloud",
            api_key=settings.MIMO_API_KEY,
            api_base=settings.MIMO_API_BASE,
            model_name=settings.MIMO_MODEL_NAME,
        )
    else:
        return LLMConfig(
            provider="local",
            api_key="not-needed",
            api_base=f"http://localhost:{settings.LOCAL_MODEL_PORT}/v1",
            model_name=settings.LOCAL_MODEL_NAME,
        )
