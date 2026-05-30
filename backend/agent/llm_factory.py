from typing import Union
from llama_index.core.llms import LLM

from backend.config.settings import get_settings
from backend.config.llm_config import get_llm_config

# 猴子补丁：允许任意模型名
def _apply_patches():
    """应用猴子补丁以支持自定义模型名"""
    import llama_index.llms.openai.utils as utils

    # 修补 is_chat_model
    if not hasattr(utils, '_patched_is_chat_model'):
        original_is_chat_model = utils.is_chat_model
        def patched_is_chat_model(model: str) -> bool:
            if model not in utils.CHAT_MODELS:
                return True
            return original_is_chat_model(model)
        utils.is_chat_model = patched_is_chat_model
        utils._patched_is_chat_model = True

    # 修补 openai_modelname_to_contextsize
    if not hasattr(utils, '_patched_contextsize'):
        original_contextsize = utils.openai_modelname_to_contextsize
        def patched_contextsize(modelname: str) -> int:
            try:
                return original_contextsize(modelname)
            except ValueError:
                return 128000
        utils.openai_modelname_to_contextsize = patched_contextsize
        utils._patched_contextsize = True

    # 将自定义模型添加到 ALL_AVAILABLE_MODELS
    settings = get_settings()
    if settings.LLM_PROVIDER == "cloud":
        model_name = settings.MIMO_MODEL_NAME
    else:
        model_name = settings.LOCAL_MODEL_NAME

    if model_name not in utils.ALL_AVAILABLE_MODELS:
        utils.ALL_AVAILABLE_MODELS[model_name] = 128000

_apply_patches()

# 导入 OpenAI（在猴子补丁之后）
from llama_index.llms.openai import OpenAI


class LLMFactory:
    """
    LLM 工厂类
    根据配置创建云端(MiMo)或本地(Qwen)的LLM实例
    """

    @staticmethod
    def create() -> LLM:
        """根据配置创建 LLM 实例"""
        config = get_llm_config()

        if config.provider == "cloud":
            return LLMFactory._create_cloud_llm(config)
        else:
            return LLMFactory._create_local_llm(config)

    @staticmethod
    def _create_cloud_llm(config) -> LLM:
        """创建云端 LLM (MiMo) - 使用 OpenAI 兼容接口"""
        import httpx
        from openai import AsyncOpenAI

        # 创建不使用代理的 httpx 客户端
        transport = httpx.AsyncHTTPTransport(proxy=None)
        http_client = httpx.AsyncClient(
            transport=transport,
            timeout=httpx.Timeout(60.0, connect=30.0),
        )

        async_client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.api_base,
            http_client=http_client,
        )

        return OpenAI(
            model=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            async_openai_client=async_client,
        )

    @staticmethod
    def _create_local_llm(config) -> LLM:
        """创建本地 LLM (Qwen) - 兼容 OpenAI API 格式"""
        import httpx
        from openai import AsyncOpenAI

        # 创建不使用代理的 httpx 客户端
        transport = httpx.AsyncHTTPTransport(proxy=None)
        http_client = httpx.AsyncClient(
            transport=transport,
            timeout=httpx.Timeout(60.0, connect=30.0),
        )

        async_client = AsyncOpenAI(
            api_key="not-needed",
            base_url=config.api_base,
            http_client=http_client,
        )

        return OpenAI(
            model=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            async_openai_client=async_client,
        )
