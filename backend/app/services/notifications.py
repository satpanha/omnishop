"""
Notification Service.

Sends alerts to the seller (owner) and order/payment/delivery messages to buyers
via Telegram. Order notifications carry **actionable inline keyboards** so the
owner can drive the workflow straight from the chat.

These functions run as background tasks. They open a FRESH database session
(``async_session``) rather than reusing a request session — a background task may
execute after the request's session has been committed/closed, so reusing it is
the footgun this feature deliberately avoids. They take an ``order_id`` and load
what they need, never a detached ORM instance.
"""

import functools
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import async_session
from app.models.order import Order
from app.models.product import Product
from app.models.transaction import Transaction
from app.services.telegram import TelegramService

logger = logging.getLogger(__name__)

LOW_STOCK_THRESHOLD = 5


def _best_effort(fn):
    """Background notifications must never raise — log and swallow everything
    (including DB-connect failures) so a post-response task can't crash."""

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - notifications are best-effort
            logger.error("notification %s failed: %s", fn.__name__, exc)
            return None

    return wrapper


# ── helpers ───────────────────────────────────────────────────────────────

def _cb(order_id, action: str) -> str:
    """Build inline-keyboard callback_data (stays well under Telegram's 64B)."""
    return f"order:{order_id}:{action}"


async def _load_lines(session: AsyncSession, order_id) -> list[tuple[str, int, float]]:
    """Return [(product_name, quantity, line_total), ...] for an order."""
    rows = (
        await session.execute(
            select(Product.name, Transaction.quantity, Transaction.total_price)
            .join(Product, Product.id == Transaction.product_id)
            .where(Transaction.order_id == order_id)
        )
    ).all()
    return [(name, qty, float(total)) for name, qty, total in rows]


def _summary_text(order: Order, lines: list[tuple[str, int, float]]) -> str:
    items = "\n".join(f"• {name} ×{qty} — ${total:.2f}" for name, qty, total in lines)
    eta = f"\n<b>ETA:</b> ~{order.eta_minutes} min" if order.eta_minutes else ""
    addr = f"\n<b>Deliver to:</b> {order.delivery_address}" if order.delivery_address else ""
    return (
        f"{items}\n\n"
        f"<b>Total:</b> ${float(order.total_amount):.2f}{eta}{addr}\n"
        f"<b>Order:</b> <code>{order.id}</code>"
    )


# ── owner-facing ──────────────────────────────────────────────────────────

@_best_effort
async def notify_owner_new_order(order_id) -> None:
    """Actionable alert to the owner when a new order is placed (awaiting payment)."""
    settings = get_settings()
    admin_id = settings.ADMIN_TELEGRAM_ID
    if not admin_id:
        logger.warning("ADMIN_TELEGRAM_ID not set; skipping owner order alert")
        return

    async with async_session() as session:
        order = (
            await session.execute(select(Order).where(Order.id == order_id))
        ).scalar_one_or_none()
        if order is None:
            return
        lines = await _load_lines(session, order_id)
        low_stock = (
            await session.execute(
                select(Product.name, Product.stock_quantity)
                .join(Transaction, Transaction.product_id == Product.id)
                .where(
                    Transaction.order_id == order_id,
                    Product.stock_quantity < LOW_STOCK_THRESHOLD,
                )
            )
        ).all()

    text = "<b>🛒 New Order — awaiting payment</b>\n\n" + _summary_text(order, lines)
    tg = TelegramService()
    keyboard = tg.inline_keyboard(
        [[
            {"text": "✅ Mark paid", "callback_data": _cb(order_id, "paid")},
            {"text": "❌ Cancel", "callback_data": _cb(order_id, "cancel")},
        ]]
    )
    try:
        await tg.send_message(chat_id=admin_id, text=text, reply_markup=keyboard)
        for name, qty in low_stock:
            await tg.send_message(
                chat_id=admin_id,
                text=f"<b>⚠️ Low stock:</b> {name} ({qty} left)",
            )
    except Exception as exc:  # noqa: BLE001 - notifications are best-effort
        logger.error("notify_owner_new_order failed: %s", exc)
    finally:
        await tg.close()


@_best_effort
async def notify_owner_order_paid(order_id) -> None:
    """Owner alert once payment is confirmed, with a one-tap dispatch action."""
    settings = get_settings()
    admin_id = settings.ADMIN_TELEGRAM_ID
    if not admin_id:
        return
    async with async_session() as session:
        order = (
            await session.execute(select(Order).where(Order.id == order_id))
        ).scalar_one_or_none()
        if order is None:
            return
        lines = await _load_lines(session, order_id)

    text = "<b>💰 Payment received</b>\n\n" + _summary_text(order, lines)
    tg = TelegramService()
    keyboard = tg.inline_keyboard(
        [[
            {"text": "📦 Mark dispatched", "callback_data": _cb(order_id, "dispatch")},
            {"text": "❌ Cancel", "callback_data": _cb(order_id, "cancel")},
        ]]
    )
    try:
        await tg.send_message(chat_id=admin_id, text=text, reply_markup=keyboard)
    except Exception as exc:  # noqa: BLE001
        logger.error("notify_owner_order_paid failed: %s", exc)
    finally:
        await tg.close()


@_best_effort
async def notify_owner_escalation(buyer_platform: str, buyer_id: str, text: str) -> None:
    """Tell the owner a buyer message needs a human (bot couldn't answer)."""
    settings = get_settings()
    admin_id = settings.ADMIN_TELEGRAM_ID
    if not admin_id:
        return
    msg = (
        "<b>💬 Buyer needs a reply</b>\n\n"
        f"<b>Platform:</b> {buyer_platform}\n"
        f"<b>Buyer:</b> <code>{buyer_id}</code>\n\n"
        f"“{text}”\n\n"
        "<i>Reply from the admin panel, or reply to this message to answer.</i>"
    )
    tg = TelegramService()
    try:
        await tg.send_message(chat_id=admin_id, text=msg)
    except Exception as exc:  # noqa: BLE001
        logger.error("notify_owner_escalation failed: %s", exc)
    finally:
        await tg.close()


# ── buyer-facing ──────────────────────────────────────────────────────────

@_best_effort
async def send_buyer_payment_request(order_id) -> None:
    """DM the buyer their order summary + KHQR payload + an ABA pay button."""
    async with async_session() as session:
        order = (
            await session.execute(select(Order).where(Order.id == order_id))
        ).scalar_one_or_none()
        if order is None:
            return
        lines = await _load_lines(session, order_id)
        payment = order.payment

    text = "<b>🧾 Your order</b>\n\n" + _summary_text(order, lines)
    if payment and payment.khqr_string:
        text += (
            "\n\n<b>Pay with KHQR</b> — scan in any banking app, or tap below.\n"
            f"<code>{payment.khqr_string}</code>"
        )
    tg = TelegramService()
    keyboard = None
    if payment and payment.aba_link:
        keyboard = tg.inline_keyboard([[{"text": "💳 Pay with ABA", "url": payment.aba_link}]])
    try:
        await tg.send_message(chat_id=order.buyer_id, text=text, reply_markup=keyboard)
    except Exception as exc:  # noqa: BLE001
        logger.error("send_buyer_payment_request failed: %s", exc)
    finally:
        await tg.close()


@_best_effort
async def send_buyer_invoice(order_id) -> None:
    """DM the buyer a paid-invoice confirmation + delivery ETA."""
    async with async_session() as session:
        order = (
            await session.execute(select(Order).where(Order.id == order_id))
        ).scalar_one_or_none()
        if order is None:
            return
        lines = await _load_lines(session, order_id)

    eta = (
        f"\n\n🛵 Estimated delivery: ~{order.eta_minutes} minutes."
        if order.eta_minutes
        else "\n\nThe seller will confirm your delivery time shortly."
    )
    text = "<b>✅ Payment received — thank you!</b>\n\n" + _summary_text(order, lines) + eta
    tg = TelegramService()
    try:
        await tg.send_message(chat_id=order.buyer_id, text=text)
    except Exception as exc:  # noqa: BLE001
        logger.error("send_buyer_invoice failed: %s", exc)
    finally:
        await tg.close()


@_best_effort
async def send_buyer_status_update(order_id, status: str) -> None:
    """DM the buyer when their order is dispatched or delivered."""
    async with async_session() as session:
        order = (
            await session.execute(select(Order).where(Order.id == order_id))
        ).scalar_one_or_none()
        if order is None:
            return

    if status == "preparing":
        text = "<b>👨‍🍳 Your order is being prepared!</b> We'll notify you when it's on the way."
    elif status == "dispatched":
        eta = f" Arriving in ~{order.eta_minutes} min." if order.eta_minutes else ""
        text = f"<b>📦 Your order is on the way!</b>{eta}"
    elif status == "delivered":
        text = "<b>🎉 Delivered.</b> Thank you for shopping with us!"
    elif status in ("cancelled", "payment_expired"):
        text = "<b>Your order was cancelled.</b> Any payment will be refunded."
    else:
        return

    tg = TelegramService()
    try:
        await tg.send_message(chat_id=order.buyer_id, text=text)
    except Exception as exc:  # noqa: BLE001
        logger.error("send_buyer_status_update failed: %s", exc)
    finally:
        await tg.close()


# ── legacy (still used by the deprecated POST /transactions path) ─────────

@_best_effort
async def notify_low_stock(product: Product) -> None:
    """Alert the admin that a product's inventory is low."""
    settings = get_settings()
    admin_id = settings.ADMIN_TELEGRAM_ID
    if not admin_id:
        return
    msg = (
        f"<b>⚠️ Low Inventory Alert!</b>\n\n"
        f"Product <b>{product.name}</b> is running low on stock.\n"
        f"<b>Remaining quantity:</b> {product.stock_quantity}\n"
        f"Please restock soon!"
    )
    telegram = TelegramService()
    try:
        await telegram.send_message(chat_id=admin_id, text=msg)
    except Exception as exc:  # noqa: BLE001
        logger.error("Error in notify_low_stock: %s", exc)
    finally:
        await telegram.close()
