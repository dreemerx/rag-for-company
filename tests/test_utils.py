"""工具函数测试"""
import pytest
from backend.chat.router import _estimate_tokens, _generate_title


def test_estimate_tokens_chinese():
    """测试中文 token 估算"""
    # 中文约 1.5 字/token
    text = "这是一段中文文本"
    tokens = _estimate_tokens(text)
    assert tokens > 0
    assert tokens < len(text)  # token 数应该少于字符数


def test_estimate_tokens_english():
    """测试英文 token 估算"""
    # 英文约 4 字符/token
    text = "This is some English text"
    tokens = _estimate_tokens(text)
    assert tokens > 0
    assert tokens < len(text)


def test_estimate_tokens_empty():
    """测试空文本"""
    assert _estimate_tokens("") == 0


def test_estimate_tokens_mixed():
    """测试中英混合文本"""
    text = "Hello 你好 World 世界"
    tokens = _estimate_tokens(text)
    assert tokens > 0


@pytest.mark.asyncio
async def test_generate_title_normal():
    """测试正常标题生成"""
    title = await _generate_title("帮我查一下今天的天气", "今天天气晴朗")
    # 去掉"帮我"前缀后是"查一下今天的天气"，再去掉"一下"不会被去掉
    assert "天气" in title
    assert title != "新对话"


@pytest.mark.asyncio
async def test_generate_title_with_punctuation():
    """测试带标点的标题生成"""
    title = await _generate_title("你好？", "你好！")
    assert title == "你好"


@pytest.mark.asyncio
async def test_generate_title_long():
    """测试长标题截断"""
    title = await _generate_title("这是一段非常非常非常非常非常非常长的问题", "回答")
    assert len(title) <= 18  # 15 + "..."
    assert title.endswith("...")


@pytest.mark.asyncio
async def test_generate_title_empty():
    """测试空标题"""
    title = await _generate_title("帮我", "好的")
    assert title == "新对话"


@pytest.mark.asyncio
async def test_generate_title_prefix_removal():
    """测试前缀移除"""
    assert await _generate_title("帮我查天气", "晴") == "查天气"
    assert await _generate_title("请帮我看看", "好的") == "帮我看看"
    assert await _generate_title("我想问一下", "答") == "问一下"
