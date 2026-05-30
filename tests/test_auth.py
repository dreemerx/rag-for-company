import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    response = await client.post("/api/v1/auth/register", json={
        "username": "newuser",
        "email": "new@example.com",
        "password": "password123",
        "full_name": "新用户",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert "user" in data["roles"]


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    response = await client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "test123456",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
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
async def test_refresh_token(client: AsyncClient):
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
