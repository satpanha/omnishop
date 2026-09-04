"""
Authentication API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_user, get_db
from app.auth.jwt_handler import clear_auth_cookie, create_access_token, set_auth_cookie
from app.auth.telegram_verify import validate_init_data
from app.config import get_settings, Settings
from app.models.seller import Seller
from app.schemas.auth import AdminLoginRequest, AuthResponse, TelegramAuthRequest, UserInfo

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


@router.post("/login", response_model=AuthResponse)
async def login_admin(
    payload: AdminLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Direct desktop browser login for the store owner.
    Authenticates against ADMIN_PASSWORD and issues an admin JWT.
    """
    if not settings.ADMIN_PASSWORD or payload.password != settings.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin password",
        )

    telegram_id = settings.ADMIN_TELEGRAM_ID

    # Ensure seller record exists
    stmt = select(Seller).where(Seller.telegram_id == telegram_id)
    seller = (await db.execute(stmt)).scalar_one_or_none()
    if not seller:
        seller = Seller(
            telegram_id=telegram_id,
            store_name="My OmniShop",
        )
        db.add(seller)
        await db.commit()
        await db.refresh(seller)

    token_payload = {
        "sub": str(telegram_id),
        "role": "admin",
    }
    token = create_access_token(token_payload)
    set_auth_cookie(response, token)

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserInfo(
            telegram_id=telegram_id,
            first_name="Store",
            last_name="Owner",
            username="admin",
            is_admin=True,
        ),
    )


@router.get("/me", response_model=UserInfo)
async def get_me(
    current_user: dict = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """
    Return the current authenticated user's profile for session rehydration.
    """
    sub = current_user.get("sub", "")
    is_admin = current_user.get("role") == "admin"
    try:
        tg_id = int(sub)
    except (ValueError, TypeError):
        tg_id = 0

    return UserInfo(
        telegram_id=tg_id,
        first_name="Store" if is_admin else "Buyer",
        last_name="Owner" if is_admin else None,
        username="admin" if is_admin else None,
        is_admin=is_admin,
    )


@router.post("/logout")
async def logout(response: Response):
    """
    Log out and clear the authentication cookie.
    """
    clear_auth_cookie(response)
    return {"status": "ok"}
