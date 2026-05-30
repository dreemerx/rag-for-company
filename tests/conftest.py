import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.database import init_db


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def setup_db():
    await init_db()
    yield


@pytest.fixture
async def client(setup_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
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
