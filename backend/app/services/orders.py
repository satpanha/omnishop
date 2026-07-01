"""
Order orchestration service.

Owns the order lifecycle that the API and webhooks drive:
  * :func:`create_order`         — cart → Order + line items + Payment (atomic)
  * :func:`apply_payment_success`— idempotent webhook-driven paid transition
  * :func:`transition_order`     — owner-driven fulfillment transitions + restock
  * :func:`run_reconciliation`   — expire stale unpaid orders (compensating job)

Validation failures raise :class:`OrderError` (transport-agnostic); the router
translates it to an ``HTTPException`` so this stays unit-testable without HTTP.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.order import Order
from app.models.payment import Payment
from app.models.product import Product
from app.models.seller import Seller
from app.models.transaction import Transaction
from app.schemas.order import DeliveryInfo, OrderLineItemCreate
from app.services import order_state
from app.services.distance import estimate_delivery
from app.services.payway import PayWayService

logger = logging.getLogger(__name__)


class OrderError(Exception):
    """Domain error with an HTTP-friendly status code + detail."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


async def _get_default_seller(db: AsyncSession, settings: Settings) -> Seller:
    """Return the single shop owner, creating the record if needed."""
    stmt = select(Seller).where(Seller.telegram_id == settings.ADMIN_TELEGRAM_ID)
    seller = (await db.execute(stmt)).scalar_one_or_none()
    if seller is None:
        seller = Seller(
            telegram_id=settings.ADMIN_TELEGRAM_ID,
            store_name="My OmniShop",
            store_lat=Decimal("11.5564"),  # Phnom Penh default
            store_lng=Decimal("104.9282"),
        )
        db.add(seller)
        await db.flush()
    return seller


async def create_order(
    db: AsyncSession,
    *,
    buyer_platform: str,
    buyer_id: str,
    items: list[OrderLineItemCreate],
    delivery: DeliveryInfo | None = None,
    idempotency_key: str | None = None,
) -> Order:
    """Create an Order (+ line items, + Payment) from a cart. Atomic."""
    settings = get_settings()
    buyer_id = str(buyer_id)

    # Idempotency: a retried submit with the same key returns the same order.
    if idempotency_key:
        existing = (
            await db.execute(
                select(Order).where(Order.idempotency_key == idempotency_key)
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing

    logger.info("[METRICS] order.create_attempt buyer=%s items=%d", buyer_id, len(items))

    seller = await _get_default_seller(db, settings)

    total = Decimal("0.00")
    line_items: list[Transaction] = []
    for item in items:
        product = (
            await db.execute(select(Product).where(Product.id == item.product_id))
        ).scalar_one_or_none()
        if product is None:
            raise OrderError(404, f"Product not found: {item.product_id}")
        if not product.is_active:
            raise OrderError(400, f"Product is inactive: {product.name}")
        if product.stock_quantity < item.quantity:
            raise OrderError(
                400,
                f"Insufficient stock for {product.name}. "
                f"Available: {product.stock_quantity}",
            )
        product.stock_quantity -= item.quantity
        line_total = product.price * item.quantity
        total += line_total
        line_items.append(
            Transaction(
                product_id=product.id,
                buyer_platform=buyer_platform,
                buyer_id=buyer_id,
                quantity=item.quantity,
                total_price=line_total,
                status="pending",
            )
        )

    # Delivery + best-effort ETA (never blocks the order).
    addr = lat = lng = None
    dist_km = eta = None
    if delivery is not None:
        addr, lat, lng = delivery.address, delivery.lat, delivery.lng
        dist_km, eta = estimate_delivery(
            seller.store_lat, seller.store_lng, lat, lng
        )

    order = Order(
        seller_id=seller.id,
        buyer_platform=buyer_platform,
        buyer_id=buyer_id,
        total_amount=total,
        currency=settings.PAYMENT_CURRENCY,
        status="awaiting_payment",
        delivery_address=addr,
        delivery_lat=lat,
        delivery_lng=lng,
        distance_km=dist_km,
        eta_minutes=eta,
        idempotency_key=idempotency_key,
        line_items=line_items,
    )
    db.add(order)
    await db.flush()

    # Payment intent (only when the feature is enabled; else legacy/manual).
    if settings.PAYMENTS_ENABLED:
        payway = PayWayService()
        result = await payway.create_purchase(
            order_id=str(order.id),
            amount=f"{total:.2f}",
            currency=order.currency,
        )
        db.add(
            Payment(
                order_id=order.id,
                provider=result.provider,
                amount=total,
                currency=order.currency,
                khqr_string=result.khqr_string,
                aba_link=result.aba_link,
                provider_txn_ref=result.provider_txn_ref,
                status="initiated" if result.status == "initiated" else "failed",
            )
        )

    await db.commit()
    await db.refresh(order)
    logger.info("Order created: %s total=%s lines=%d", order.id, total, len(line_items))
    logger.info("[AUDIT] order.created order_id=%s buyer=%s total=%s", order.id, buyer_id, total)
    return order


async def apply_payment_success(
    db: AsyncSession, payment: Payment, raw_callback: dict | None = None
) -> Order:
    """
    Mark a payment paid and advance its order. Idempotent: a duplicate/replayed
    callback for an already-paid payment is a no-op. This is the only place that
    sets ``payment.status = 'paid'``.
    """
    order = (
        await db.execute(select(Order).where(Order.id == payment.order_id))
    ).scalar_one()

    if payment.status == "paid":
        logger.info("[AUDIT] payment.replay_ignored order_id=%s payment_id=%s", order.id, payment.id)
        return order  # already settled — replay-safe no-op

    payment.status = "paid"
    payment.paid_at = datetime.now(timezone.utc)
    if raw_callback is not None:
        payment.raw_callback = raw_callback

    if order.status == "awaiting_payment":
        order.status = "paid"

    await db.commit()
    await db.refresh(order)
    logger.info("Payment settled for order %s (payment %s)", order.id, payment.id)
    logger.info("[AUDIT] payment.settled order_id=%s payment_id=%s", order.id, payment.id)
    return order


async def transition_order(
    db: AsyncSession,
    order: Order,
    new_status: str,
    *,
    eta_minutes: int | None = None,
    dispatch_at: datetime | None = None,
) -> Order:
    """
    Owner-driven fulfillment transition. Validates against the state machine,
    restocks on cancel/expire, and stamps ETA/dispatch time on dispatch.
    Re-applying the current status is a no-op (safe to retry).
    """
    if order.status == new_status:
        return order

    logger.info("[AUDIT] order.transition order_id=%s %s->%s", order.id, order.status, new_status)

    order_state.assert_transition(order.status, new_status)

    if new_status in order_state.RESTOCK_ON:
        await _restock(db, order)

    if new_status == "dispatched":
        order.dispatch_at = dispatch_at or datetime.now(timezone.utc)

    if eta_minutes is not None:
        order.eta_minutes = eta_minutes

    order.status = new_status
    await db.commit()
    await db.refresh(order)
    logger.info("Order %s → %s", order.id, new_status)
    return order


async def _restock(db: AsyncSession, order: Order) -> None:
    """Return each line item's quantity to product inventory."""
    for line in order.line_items:
        product = (
            await db.execute(select(Product).where(Product.id == line.product_id))
        ).scalar_one_or_none()
        if product is not None:
            product.stock_quantity += line.quantity


async def run_reconciliation(db: AsyncSession) -> dict[str, int]:
    """
    Compensating job: expire orders that have sat unpaid past the TTL (restocking
    them). In live mode this is also where you'd re-query PayWay for orders whose
    callback may have been missed. Returns a small summary for logging/alerting.
    """
    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.PAYMENT_TTL_MINUTES)
    stale = (
        await db.execute(
            select(Order).where(
                Order.status == "awaiting_payment",
                Order.created_at < cutoff,
            )
        )
    ).scalars().all()

    expired = 0
    for order in stale:
        await transition_order(db, order, "payment_expired")
        expired += 1

    if expired:
        logger.info("Reconciliation expired %d stale unpaid orders", expired)
    logger.info("[METRICS] reconciliation.run expired=%d", expired)
    return {"expired": expired}
