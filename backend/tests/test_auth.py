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
