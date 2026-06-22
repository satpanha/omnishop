"""
Authentication API endpoints.
"""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db
from app.auth.jwt_handler import create_access_token, set_auth_cookie
from app.auth.telegram_verify import validate_init_data
from app.config import get_settings, Settings
from app.models.seller import Seller
from app.schemas.auth import TelegramAuthRequest, AuthResponse, UserInfo

router = APIRouter()


@router.post("/telegram", response_model=AuthResponse)
async def authenticate_telegram(
    payload: TelegramAuthRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Authenticate a user coming from the Telegram Mini App.
    Validates initData, determines role, and issues a JWT token.
    """
    # In development mode, we can bypass validation if the string is simple or mock
    if settings.ENVIRONMENT == "development" and payload.initData.startswith("mock_"):
        # Create a mock user based on the mock string
        mock_id = 999999999
        if "admin" in payload.initData:
            mock_id = settings.ADMIN_TELEGRAM_ID
        
        user_data = {
            "id": mock_id,
            "first_name": "Mock",
            "last_name": "User",
            "username": "mock_user",
        }
    else:
        user_data = validate_init_data(payload.initData, settings.TELEGRAM_BOT_TOKEN)

    telegram_id = user_data["id"]
    is_admin = (telegram_id == settings.ADMIN_TELEGRAM_ID)
    role = "admin" if is_admin else "buyer"

    # If the user is admin, make sure we have a Seller record for them
    if is_admin:
        # Check if seller exists
        stmt = select(Seller).where(Seller.telegram_id == telegram_id)
        result = await db.execute(stmt)
        seller = result.scalar_one_or_none()
        if not seller:
            seller = Seller(
                telegram_id=telegram_id,
                store_name="My OmniShop",
            )
            db.add(seller)
            await db.commit()
            await db.refresh(seller)

    # Issue JWT token
    token_payload = {
        "sub": str(telegram_id),
        "role": role,
    }
    token = create_access_token(token_payload)

    # Set httpOnly secure cookie
    set_auth_cookie(response, token)

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserInfo(
            telegram_id=telegram_id,
            first_name=user_data.get("first_name", ""),
            last_name=user_data.get("last_name"),
            username=user_data.get("username"),
            is_admin=is_admin,
        ),
    )
