"""
FastAPI dependency injection helper functions.
"""

from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyCookie, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db as db_generator
from app.auth.jwt_handler import COOKIE_NAME, verify_token

# Define security schemes for docs
cookie_scheme = APIKeyCookie(name=COOKIE_NAME, auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Pass-through wrapper for database session dependency."""
    async for session in db_generator():
        yield session


def get_token(
    request: Request,
    cookie_token: Optional[str] = Depends(cookie_scheme),
    bearer_token: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[str]:
    """Retrieve token from cookie or Authorization header."""
    if cookie_token:
        return cookie_token
    if bearer_token:
        return bearer_token.credentials
    return None


async def get_current_user(token: Optional[str] = Depends(get_token)) -> dict:
    """
    Retrieve and verify JWT payload.
    Returns:
        dict: JWT payload containing 'sub' (telegram_id) and 'role'.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated: missing token",
        )
    return verify_token(token)


async def get_current_user_optional(token: Optional[str] = Depends(get_token)) -> Optional[dict]:
    """
    Retrieve and verify JWT payload, returning None if missing or invalid.
    """
    if not token:
        return None
    try:
        return verify_token(token)
    except HTTPException:
        return None


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Ensure the current user has the 'admin' role.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Admin access required",
        )
    return current_user
