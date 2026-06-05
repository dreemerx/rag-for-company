import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# 设置测试环境变量（必须在导入 app 之前）
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./data/test.db")

from backend.main import app
from backend.database import init_db


@pytest_asyncio.fixture(scope="session")
async def setup_db():
    """初始化测试数据库"""
    await init_db()
    yield


@pytest_asyncio.fixture
async def client(setup_db):
    """获取测试客户端"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient):
    """获取认证 headers"""
    # 注册用户
    await client.post("/api/v1/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "test123456",
        "full_name": "测试用户",
        "department": "技术部",
    })

    # 登录
    response = await client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "test123456",
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
