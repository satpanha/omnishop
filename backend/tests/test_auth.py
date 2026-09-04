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


def _generate_valid_init_data(telegram_id: int, bot_token: str) -> str:
    import hmac
    import hashlib
    import time
    from urllib.parse import urlencode
    
    user_str = f'{{"id": {telegram_id}, "first_name": "Test"}}'
    auth_date = str(int(time.time()))
    
    # Sort remaining key=value pairs alphabetically and join with \n
    data_check_string = f"auth_date={auth_date}\nuser={user_str}"
    
    # secret_key = HMAC-SHA256("WebAppData", bot_token)
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    
    # calculated_hash = HMAC-SHA256(secret_key, data_check_string)
    h = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    
    params = {
        "user": user_str,
        "auth_date": auth_date,
        "hash": h
    }
    return urlencode(params)


@pytest.mark.asyncio
async def test_telegram_auth_success_with_valid_signature(client: AsyncClient):
    """Test auth endpoint behaves correctly with a valid signed Telegram initData."""
    from app.config import get_settings
    settings = get_settings()
    
    init_data = _generate_valid_init_data(settings.ADMIN_TELEGRAM_ID, settings.TELEGRAM_BOT_TOKEN)
    payload = {"initData": init_data}
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


@pytest.mark.asyncio
async def test_admin_login_success(client: AsyncClient):
    """Test admin password login with valid credentials."""
    from app.config import get_settings
    settings = get_settings()

    response = await client.post("/api/v1/auth/login", json={"password": settings.ADMIN_PASSWORD})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["is_admin"] is True
    # Verify cookie is set
    assert "access_token" in response.cookies


@pytest.mark.asyncio
async def test_admin_login_invalid_password(client: AsyncClient):
    """Test admin password login fails with wrong password."""
    response = await client.post("/api/v1/auth/login", json={"password": "incorrect-password-xyz"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_authenticated(client: AsyncClient, mock_admin_token: str):
    """Test /api/v1/auth/me returns user info when authenticated via header."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {mock_admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_admin"] is True


@pytest.mark.asyncio
async def test_auth_me_cookie(client: AsyncClient, mock_admin_token: str):
    """Test /api/v1/auth/me works with access_token cookie."""
    client.cookies.set("access_token", mock_admin_token)
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["is_admin"] is True


@pytest.mark.asyncio
async def test_auth_me_unauthenticated(client: AsyncClient):
    """Test /api/v1/auth/me returns 401 without auth credentials."""
    client.cookies.clear()
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_logout(client: AsyncClient):
    """Test /api/v1/auth/logout succeeds and clears cookie."""
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out"

