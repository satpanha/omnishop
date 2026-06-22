"""
Pydantic v2 schemas for authentication endpoints.
"""

from pydantic import BaseModel


class TelegramAuthRequest(BaseModel):
    """Payload from the Telegram Mini App containing initData."""
    initData: str


class UserInfo(BaseModel):
    """Basic user information returned after authentication."""
    telegram_id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    is_admin: bool


class AuthResponse(BaseModel):
    """Response after successful authentication."""
    access_token: str
    token_type: str = "bearer"
    user: UserInfo
