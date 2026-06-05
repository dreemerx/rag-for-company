import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    # 使用唯一用户名避免冲突
    unique_name = f"reguser_{uuid.uuid4().hex[:8]}"
    response = await client.post("/api/v1/auth/register", json={
        "username": unique_name,
        "email": f"{unique_name}@example.com",
        "password": "password123",
        "full_name": "注册用户",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == unique_name
    assert "user" in data["roles"]


@pytest.mark.asyncio
async def test_register_duplicate(client: AsyncClient):
    """测试重复注册"""
    unique_name = f"dupuser_{uuid.uuid4().hex[:8]}"
    # 第一次注册
    await client.post("/api/v1/auth/register", json={
        "username": unique_name,
        "email": f"{unique_name}@example.com",
        "password": "password123",
    })
    # 第二次注册相同用户名
    response = await client.post("/api/v1/auth/register", json={
        "username": unique_name,
        "email": f"other_{unique_name}@example.com",
        "password": "password123",
    })
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    """测试短密码"""
    response = await client.post("/api/v1/auth/register", json={
        "username": f"shortpw_{uuid.uuid4().hex[:8]}",
        "email": "short@example.com",
        "password": "123",
    })
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_login(client: AsyncClient, auth_headers: dict):
    # auth_headers fixture 已注册并登录了 testuser
    # 直接用同样的凭据测试登录
    response = await client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "test123456",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, auth_headers: dict):
    response = await client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, auth_headers: dict):
    # 先登录获取 refresh token
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "test123456",
    })
    refresh_token = login_response.json()["refresh_token"]

    # 刷新 token
    response = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
