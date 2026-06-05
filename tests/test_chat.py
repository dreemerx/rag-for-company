"""对话模块测试"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_session(client: AsyncClient, auth_headers: dict):
    """测试创建对话"""
    response = await client.post(
        "/api/v1/chat/sessions",
        json={"title": "测试对话"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "测试对话"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_sessions(client: AsyncClient, auth_headers: dict):
    """测试获取对话列表"""
    # 先创建一个对话
    await client.post(
        "/api/v1/chat/sessions",
        json={"title": "列表测试"},
        headers=auth_headers,
    )

    response = await client.get("/api/v1/chat/sessions", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_update_session(client: AsyncClient, auth_headers: dict):
    """测试更新对话标题"""
    # 创建对话
    create_response = await client.post(
        "/api/v1/chat/sessions",
        json={"title": "原始标题"},
        headers=auth_headers,
    )
    session_id = create_response.json()["id"]

    # 更新标题
    response = await client.patch(
        f"/api/v1/chat/sessions/{session_id}",
        json={"title": "新标题"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["title"] == "新标题"


@pytest.mark.asyncio
async def test_delete_session(client: AsyncClient, auth_headers: dict):
    """测试删除对话"""
    # 创建对话
    create_response = await client.post(
        "/api/v1/chat/sessions",
        json={"title": "待删除"},
        headers=auth_headers,
    )
    session_id = create_response.json()["id"]

    # 删除对话
    response = await client.delete(
        f"/api/v1/chat/sessions/{session_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200

    # 验证已删除
    get_response = await client.get(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=auth_headers,
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_get_messages_empty(client: AsyncClient, auth_headers: dict):
    """测试获取空对话的消息"""
    # 创建对话
    create_response = await client.post(
        "/api/v1/chat/sessions",
        json={"title": "空消息测试"},
        headers=auth_headers,
    )
    session_id = create_response.json()["id"]

    # 获取消息
    response = await client.get(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    """测试未授权访问"""
    response = await client.get("/api/v1/chat/sessions")
    assert response.status_code in (401, 403)  # 未认证
