"""
Authentication API tests.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_returns_200(client: AsyncClient):
    """Test health check path."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_root_returns_info(client: AsyncClient):
    """Test root path."""
    response = await client.get("/")
    assert response.status_code == 200
    assert "name" in response.json()


@pytest.mark.asyncio
async def test_telegram_auth_mock_success(client: AsyncClient):
    """Test auth endpoint behaves correctly with mock payloads in development mode."""
    # Send request with mock data
    payload = {"initData": "mock_admin_user"}
    response = await client.post("/api/v1/auth/telegram", json=payload)
    
    assert response.status_code == 200
    res_data = response.json()
    assert "access_token" in res_data
    assert res_data["token_type"] == "bearer"
    assert res_data["user"]["is_admin"] is True


@pytest.mark.asyncio
async def test_telegram_auth_invalid_data_returns_401(client: AsyncClient):
    """Test that actual invalid initData fails validation with 401."""
    # Real signature verification will fail for this dummy string
    payload = {"initData": "user=%7B%22id%22%3A123%7D&hash=invalidhash"}
    response = await client.post("/api/v1/auth/telegram", json=payload)
    assert response.status_code == 401
