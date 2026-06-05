"""配置模块测试"""
import pytest
import warnings
from backend.config.settings import Settings, _validate_settings


def test_settings_default_values():
    """测试配置默认值"""
    settings = Settings()
    assert settings.LLM_PROVIDER == "cloud"
    assert settings.MILVUS_DIMENSION == 512
    assert settings.EMBEDDING_MODEL == "BAAI/bge-small-zh-v1.5"
    assert settings.RATE_LIMIT_PER_MINUTE == 20


def test_jwt_secret_validation():
    """测试 JWT 密钥验证"""
    # 测试空密钥自动生成
    settings = Settings(JWT_SECRET_KEY="")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        validated = _validate_settings(settings)
        assert len(w) == 1
        assert "JWT_SECRET_KEY" in str(w[0].message)
        assert validated.JWT_SECRET_KEY != ""
        assert len(validated.JWT_SECRET_KEY) > 20


def test_jwt_secret_default_warning():
    """测试默认密钥警告"""
    settings = Settings(JWT_SECRET_KEY="your-secret-key-change-in-production")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        validated = _validate_settings(settings)
        assert len(w) == 1
        assert validated.JWT_SECRET_KEY != "your-secret-key-change-in-production"


def test_jwt_secret_custom():
    """测试自定义密钥"""
    custom_key = "my-super-secret-key-12345"
    settings = Settings(JWT_SECRET_KEY=custom_key)
    validated = _validate_settings(settings)
    assert validated.JWT_SECRET_KEY == custom_key


def test_embedding_dimension_consistency():
    """测试 Embedding 维度一致性"""
    settings = Settings()
    # 默认配置应该一致
    assert settings.MILVUS_DIMENSION == 512
    assert settings.EMBEDDING_MODEL == "BAAI/bge-small-zh-v1.5"  # 512 维
