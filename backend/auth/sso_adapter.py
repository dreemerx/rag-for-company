from abc import ABC, abstractmethod
from typing import Optional
from .models import User


class SSOAdapter(ABC):
    """
    SSO 适配器抽象基类
    用于对接企业飞书、企业微信等 SSO 系统
    """

    @abstractmethod
    async def authenticate(self, code: str) -> Optional[dict]:
        """
        通过 SSO code 进行认证
        返回用户信息字典或 None
        """
        pass

    @abstractmethod
    async def get_user_info(self, access_token: str) -> Optional[dict]:
        """
        通过 SSO access_token 获取用户详细信息
        """
        pass

    @abstractmethod
    async def sync_user_to_local(self, sso_user_info: dict) -> User:
        """
        将 SSO 用户信息同步到本地数据库
        """
        pass


class FeishuSSOAdapter(SSOAdapter):
    """飞书 SSO 适配器（示例实现）"""

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret

    async def authenticate(self, code: str) -> Optional[dict]:
        # TODO: 实现飞书 OAuth 认证流程
        raise NotImplementedError("飞书 SSO 尚未实现")

    async def get_user_info(self, access_token: str) -> Optional[dict]:
        # TODO: 调用飞书 API 获取用户信息
        raise NotImplementedError("飞书 SSO 尚未实现")

    async def sync_user_to_local(self, sso_user_info: dict) -> User:
        # TODO: 同步飞书用户到本地数据库
        raise NotImplementedError("飞书 SSO 尚未实现")


class WeChatWorkSSOAdapter(SSOAdapter):
    """企业微信 SSO 适配器（示例实现）"""

    def __init__(self, corp_id: str, agent_id: str, secret: str):
        self.corp_id = corp_id
        self.agent_id = agent_id
        self.secret = secret

    async def authenticate(self, code: str) -> Optional[dict]:
        # TODO: 实现企业微信 OAuth 认证流程
        raise NotImplementedError("企业微信 SSO 尚未实现")

    async def get_user_info(self, access_token: str) -> Optional[dict]:
        # TODO: 调用企业微信 API 获取用户信息
        raise NotImplementedError("企业微信 SSO 尚未实现")

    async def sync_user_to_local(self, sso_user_info: dict) -> User:
        # TODO: 同步企业微信用户到本地数据库
        raise NotImplementedError("企业微信 SSO 尚未实现")


def get_sso_adapter(provider: str, **kwargs) -> SSOAdapter:
    """SSO 适配器工厂函数"""
    adapters = {
        "feishu": FeishuSSOAdapter,
        "wechat_work": WeChatWorkSSOAdapter,
    }
    adapter_class = adapters.get(provider)
    if not adapter_class:
        raise ValueError(f"不支持的 SSO 提供商: {provider}")
    return adapter_class(**kwargs)
