"""
Webhook endpoints: Telegram bot updates, Instagram DMs, and ABA PayWay callbacks.

Telegram/Instagram message processing runs in background tasks (HTTP 200 fast).
The PayWay callback is processed inline because it is the **source of truth** for
payment and must verify its HMAC signature and update state transactionally.

Background workers open their OWN database session (``async_session``) rather than
reusing the request session — a task may run after the request session closed.
"""

import hashlib
import hmac
import json
import logging
import re
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import Settings, get_settings
from app.database import async_session
from app.models.order import Order
from app.models.payment import Payment
from app.services import conversations, notifications, orders
from app.services.instagram import InstagramService
from app.services.order_state import InvalidTransition
from app.services.payway import PayWayService
from app.services.telegram import TelegramService

router = APIRouter()
logger = logging.getLogger(__name__)

# Owner inline-button action → target order status.
_CALLBACK_ACTIONS = {
    "paid": "paid",
    "cancel": "cancelled",
    "dispatch": "dispatched",
    "deliver": "delivered",
}
_BUYER_ID_RE = re.compile(r"Buyer:\s*([0-9]+)")


# ── Telegram ───────────────────────────────────────────────────────────────

async def process_telegram_update(update_data: dict) -> None:
    """Background worker: dispatch a Telegram update (own DB session)."""
    try:
        async with async_session() as db:
            if "callback_query" in update_data:
                await _handle_callback_query(db, update_data["callback_query"])
            elif "message" in update_data:
                await _handle_telegram_message(db, update_data["message"])
    except Exception as exc:  # noqa: BLE001 - never let a webhook task crash
        logger.error("Error processing Telegram update: %s", exc)


async def _handle_callback_query(db: AsyncSession, cq: dict) -> None:
    """Owner pressed an inline button on an order alert → drive the workflow."""
    settings = get_settings()
    cq_id = cq.get("id")
    data = cq.get("data", "")
    from_id = cq.get("from", {}).get("id")

    tg = TelegramService()
    try:
        if str(from_id) != str(settings.ADMIN_TELEGRAM_ID):
            logger.warning(
                "[SECURITY] callback_query.unauthorized telegram_id=%s", from_id
            )
            await tg.answer_callback_query(cq_id, "Not authorized")
            return

        parts = data.split(":")
        if len(parts) != 3 or parts[0] != "order":
            await tg.answer_callback_query(cq_id, "Unknown action")
            return
        _, order_id, action = parts
        target = _CALLBACK_ACTIONS.get(action)
        if target is None:
            await tg.answer_callback_query(cq_id, "Unknown action")
            return

        order = (
            await db.execute(select(Order).where(Order.id == order_id))
        ).scalar_one_or_none()
        if order is None:
            await tg.answer_callback_query(cq_id, "Order not found")
            return

        try:
            order = await orders.transition_order(db, order, target)
        except InvalidTransition:
            await tg.answer_callback_query(cq_id, f"Can't move to {target} now")
            return

        await tg.answer_callback_query(cq_id, f"Order → {target}")
    finally:
        await tg.close()

    # Buyer notifications (best-effort; each guards its own errors).
    if target in ("dispatched", "delivered", "cancelled"):
        await notifications.send_buyer_status_update(order_id, target)
    elif target == "paid":
        await notifications.send_buyer_invoice(order_id)


async def _handle_telegram_message(db: AsyncSession, message: dict) -> None:
    """Route an inbound Telegram message: owner reply relay, or buyer Q&A."""
    settings = get_settings()
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text")
    from_id = message.get("from", {}).get("id")
    if not chat_id or not text:
        return

    is_owner = str(from_id) == str(settings.ADMIN_TELEGRAM_ID)

    # Owner replying to an escalation notification → relay to that buyer.
    if is_owner:
        replied = (message.get("reply_to_message") or {}).get("text", "")
        match = _BUYER_ID_RE.search(replied)
        if match:
            buyer_id = match.group(1)
            conv = await conversations.get_or_create_conversation(db, "telegram", buyer_id)
            await conversations.send_owner_message(db, conv, text)
        # Owner's own non-reply chatter is ignored (not a buyer query).
        return

    # Buyer message → auto-respond or escalate.
    result = await conversations.handle_inbound_message(db, "telegram", chat_id, text)
    if result.reply:
        tg = TelegramService()
        try:
            await tg.send_message(chat_id=chat_id, text=result.reply)
        finally:
            await tg.close()
    elif result.escalated:
        await notifications.notify_owner_escalation("telegram", str(chat_id), text)


@router.post("/telegram")
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: Optional[str] = Header(
        None, alias="X-Telegram-Bot-Api-Secret-Token"
    ),
    settings: Settings = Depends(get_settings),
):
    """Handle Telegram Bot API updates. Returns 200 immediately."""
    if settings.TELEGRAM_WEBHOOK_SECRET:
        if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
            logger.warning("Unauthorized Telegram webhook: secret token mismatch.")
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid webhook secret token")

    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Malformed JSON body") from exc

    background_tasks.add_task(process_telegram_update, body)
    return {"status": "ok"}


# ── Instagram ──────────────────────────────────────────────────────────────

async def process_instagram_update(entry_data: dict) -> None:
    """Background worker: Instagram DM → conversation auto-respond/escalate."""
    try:
        async with async_session() as db:
            for entry in entry_data.get("entry", []):
                for messaging in entry.get("messaging", []):
                    sender_id = messaging.get("sender", {}).get("id")
                    text = messaging.get("message", {}).get("text")
                    if not sender_id or not text:
                        continue
                    result = await conversations.handle_inbound_message(
                        db, "instagram", sender_id, text
                    )
                    if result.reply:
                        ig = InstagramService()
                        try:
                            await ig.send_reply(recipient_id=sender_id, text=result.reply)
                        finally:
                            await ig.close()
                    elif result.escalated:
                        await notifications.notify_owner_escalation(
                            "instagram", str(sender_id), text
                        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Error processing Instagram update: %s", exc)


@router.get("/instagram")
async def instagram_verify(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    settings: Settings = Depends(get_settings),
):
    """Verify Instagram webhook endpoint during setup (Meta App Challenge)."""
    if hub_mode == "subscribe" and hub_verify_token == settings.INSTAGRAM_VERIFY_TOKEN:
        from fastapi.responses import PlainTextResponse

        return PlainTextResponse(content=hub_challenge)
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Verification token mismatch")


@router.post("/instagram")
async def instagram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    settings: Settings = Depends(get_settings),
):
    """Handle Instagram Graph API messages. Returns 200 immediately."""
    raw_body = await request.body()

    if settings.INSTAGRAM_APP_SECRET and x_hub_signature_256:
        if not x_hub_signature_256.startswith("sha256="):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid signature format")
        expected = hmac.new(
            settings.INSTAGRAM_APP_SECRET.encode("utf-8"), raw_body, hashlib.sha256
        ).hexdigest()
        provided = x_hub_signature_256.split("sha256=")[1]
        if not hmac.compare_digest(expected, provided):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid signature")

    try:
        body = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Malformed JSON body") from exc

    background_tasks.add_task(process_instagram_update, body)
    return {"status": "ok"}


# ── ABA PayWay (source of truth for payment) ─────────────────────────────────

def _payway_is_success(data: dict) -> bool:
    """Interpret a PayWay callback as success across common field conventions."""
    status_val = str(data.get("status", data.get("status_code", ""))).lower()
    return status_val in {"paid", "success", "approved", "completed", "0", "00"}


@router.post("/payway")
async def payway_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_payway_signature: Optional[str] = Header(None, alias="X-Payway-Signature"),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    ABA PayWay server-to-server payment callback. Verifies the HMAC signature,
    then idempotently settles the matching payment. An unsigned/spoofed callback
    can never advance payment state (401, no DB change).
    """
    raw_body = await request.body()
    if not PayWayService.verify_callback(
        raw_body, x_payway_signature, settings.ABA_PAYWAY_CALLBACK_SECRET
    ):
        logger.warning(
            "[SECURITY] payway.invalid_signature from=%s",
            request.client.host if request.client else "unknown",
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid callback signature")

    try:
        data = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Malformed JSON body") from exc

    txn_ref = data.get("tran_id") or data.get("provider_txn_ref")
    if not txn_ref:
        return {"status": "ignored", "reason": "no transaction reference"}

    payment = (
        await db.execute(
            select(Payment).where(Payment.provider_txn_ref == str(txn_ref))
        )
    ).scalar_one_or_none()
    if payment is None:
        # Unknown ref — 200 so the provider stops retrying; nothing to settle.
        return {"status": "ignored", "reason": "unknown transaction reference"}

    if not _payway_is_success(data):
        if payment.status == "initiated":
            payment.status = "failed"
            payment.raw_callback = data
            await db.commit()
        return {"status": "recorded", "result": "not_successful"}

    order = await orders.apply_payment_success(db, payment, raw_callback=data)

    # Out-of-band: confirm to buyer + alert owner that it's paid.
    background_tasks.add_task(notifications.send_buyer_invoice, order.id)
    background_tasks.add_task(notifications.notify_owner_order_paid, order.id)
    return {"status": "ok"}
