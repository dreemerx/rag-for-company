"""
LLM 配置模块
- 封装 LLM 连接配置
- 根据 provider 自动选择云端或本地配置
"""
from dataclasses import dataclass
from functools import lru_cache
from .settings import get_settings


@dataclass
class LLMConfig:
    """
    LLM 配置数据类

    Attributes:
        provider: 提供商（cloud/local）
        api_key: API 密钥
        api_base: API 基础 URL
        model_name: 模型名称
        max_tokens: 最大生成 Token 数
        temperature: 生成温度（0-1）
    """
    provider: str
    api_key: str
    api_base: str
    model_name: str
    max_tokens: int = 4096
    temperature: float = 0.7


@lru_cache()
def get_llm_config() -> LLMConfig:
    """
    根据当前设置获取 LLM 配置（LRU 缓存单例）

    Returns:
        LLM 配置对象
    """
    settings = get_settings()

    if settings.LLM_PROVIDER == "cloud":
        # 云端配置（MiMo API）
        return LLMConfig(
            provider="cloud",
            api_key=settings.MIMO_API_KEY,
            api_base=settings.MIMO_API_BASE,
            model_name=settings.MIMO_MODEL_NAME,
        )
    else:
        # 本地配置（Qwen 本地部署）
        return LLMConfig(
            provider="local",
            api_key="not-needed",
            api_base=f"http://localhost:{settings.LOCAL_MODEL_PORT}/v1",
            model_name=settings.LOCAL_MODEL_NAME,
        )
