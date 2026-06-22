"""
JWT creation and verification utilities.

Tokens carry:
  - sub : the user's Telegram ID (as string)
  - role: 'admin' or 'buyer'
  - exp : expiration timestamp
  - iat : issued-at timestamp

Also includes helpers to set / clear httpOnly secure auth cookies.
"""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Response, status
from jose import JWTError, jwt

from app.config import get_settings

COOKIE_NAME = "omnishop_token"


def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        data: Payload dict (must include 'sub' and 'role').
        expires_delta: Optional custom expiration. Defaults to settings value.

    Returns:
        Encoded JWT string.
    """
    settings = get_settings()
    to_encode = data.copy()

    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    to_encode.update({"exp": expire, "iat": now})

    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def verify_token(token: str) -> dict:
    """
    Decode and verify a JWT token.

    Args:
        token: The encoded JWT string.

    Returns:
        Decoded payload dict.

    Raises:
        HTTPException(401): If the token is invalid or expired.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("sub") is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
            )
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
        ) from exc


def set_auth_cookie(response: Response, token: str) -> None:
    """Set an httpOnly secure cookie containing the JWT."""
    settings = get_settings()
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=(settings.ENVIRONMENT != "development"),
        samesite="lax",
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    """Delete the auth cookie."""
    response.delete_cookie(
        key=COOKIE_NAME,
        httponly=True,
        path="/",
    )
