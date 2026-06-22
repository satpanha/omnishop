"""
Telegram and Instagram Webhook Endpoints.
Process incoming social messages asynchronously in background tasks to ensure <200ms responses.
"""

import hmac
import hashlib
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import get_settings, Settings
from app.services.auto_responder import find_response
from app.services.telegram import TelegramService
from app.services.instagram import InstagramService

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Telegram Webhook Handlers ──────────────────────────────────────────

async def process_telegram_update(update_data: dict, db: AsyncSession):
    """Asynchronous background worker to process Telegram update and reply."""
    try:
        message = update_data.get("message")
        if not message:
            return

        chat_id = message.get("chat", {}).get("id")
        text = message.get("text")
        
        if not chat_id or not text:
            return

        # Query auto-responder
        reply_text = await find_response(db, text)
        
        if reply_text:
            telegram = TelegramService()
            await telegram.send_message(chat_id=chat_id, text=reply_text)
            await telegram.close()
            
    except Exception as exc:
        logger.error("Error processing Telegram update in background: %s", exc)


@router.post("/telegram")
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None, alias="X-Telegram-Bot-Api-Secret-Token"),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Handle incoming updates from the Telegram Bot API.
    Returns HTTP 200 immediately and runs processing in a background task.
    """
    # Verify Telegram secret token if configured
    if settings.TELEGRAM_WEBHOOK_SECRET:
        if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
            logger.warning("Unauthorized webhook access attempt: Secret token mismatch.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook secret token",
            )

    try:
        body = await request.json()
    except Exception as exc:
        logger.error("Malformed JSON payload in webhook: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON body",
        )

    background_tasks.add_task(process_telegram_update, body, db)
    return {"status": "ok"}


# ── Instagram Webhook Handlers ─────────────────────────────────────────

async def process_instagram_update(entry_data: dict, db: AsyncSession):
    """Asynchronous background worker to process Instagram DM update and reply."""
    try:
        # Instagram payload path: entry[] -> messaging[] -> message
        for entry in entry_data.get("entry", []):
            for messaging in entry.get("messaging", []):
                sender_id = messaging.get("sender", {}).get("id")
                message = messaging.get("message", {})
                text = message.get("text")

                if not sender_id or not text:
                    continue

                # Query auto-responder
                reply_text = await find_response(db, text)

                if reply_text:
                    instagram = InstagramService()
                    await instagram.send_reply(recipient_id=sender_id, text=reply_text)
                    await instagram.close()

    except Exception as exc:
        logger.error("Error processing Instagram update in background: %s", exc)


@router.get("/instagram")
async def instagram_verify(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    settings: Settings = Depends(get_settings),
):
    """Verify Instagram webhook endpoint during setup (Meta App Challenge)."""
    if hub_mode == "subscribe":
        if hub_verify_token == settings.INSTAGRAM_VERIFY_TOKEN:
            # Must return the hub.challenge as plain text integer/string
            from fastapi.responses import PlainTextResponse
            return PlainTextResponse(content=hub_challenge)
        else:
            logger.warning("Instagram subscription verification failed: token mismatch.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Verification token mismatch",
            )
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid hub.mode")


@router.post("/instagram")
async def instagram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Handle incoming messages from the Instagram Graph API.
    Returns HTTP 200 immediately and runs processing in a background task.
    """
    raw_body = await request.body()
    
    # Verify signature if secret is configured
    if settings.INSTAGRAM_APP_SECRET and x_hub_signature_256:
        if not x_hub_signature_256.startswith("sha256="):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature format")
        
        expected_sig = hmac.new(
            key=settings.INSTAGRAM_APP_SECRET.encode("utf-8"),
            msg=raw_body,
            digestmod=hashlib.sha256,
        ).hexdigest()
        
        provided_sig = x_hub_signature_256.split("sha256=")[1]
        if not hmac.compare_digest(expected_sig, provided_sig):
            logger.warning("Instagram signature verification failed.")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    try:
        body = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        logger.error("Malformed JSON payload in Instagram webhook: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON body",
        )

    background_tasks.add_task(process_instagram_update, body, db)
    return {"status": "ok"}
