"""
Orders API endpoints.

An Order is the payable aggregate created at checkout. Buyers create + view their
own orders and poll for payment; the owner (admin) lists all orders and drives the
fulfillment state machine.
"""

import uuid
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_admin
from app.config import get_settings
from app.models.order import Order
from app.schemas.order import (
    OrderCreate,
    OrderList,
    OrderResponse,
    OrderStatusUpdate,
)
from app.services import notifications, orders
from app.services.order_state import InvalidTransition

router = APIRouter()


async def _load_order_or_404(db: AsyncSession, order_id: uuid.UUID) -> Order:
    order = (
        await db.execute(select(Order).where(Order.id == order_id))
    ).scalar_one_or_none()
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return order


def _assert_order_access(order: Order, current_user: dict) -> None:
    """Admin OR the owning buyer — mirrors transactions.get_transaction."""
    is_admin = current_user.get("role") == "admin"
    is_buyer = order.buyer_id == current_user.get("sub")
    if not (is_admin or is_buyer):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create an order from the buyer's cart and return the payment QR / link."""
    try:
        order = await orders.create_order(
            db,
            buyer_platform="telegram",
            buyer_id=current_user["sub"],
            items=payload.items,
            delivery=payload.delivery,
            idempotency_key=payload.idempotency_key,
        )
    except orders.OrderError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc

    # Out-of-band: alert the owner, and DM the buyer their payment request.
    background_tasks.add_task(notifications.notify_owner_new_order, order.id)
    if get_settings().PAYMENTS_ENABLED and order.payment is not None:
        background_tasks.add_task(notifications.send_buyer_payment_request, order.id)

    return order


@router.get("", response_model=OrderList)
async def list_orders(
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    admin_user: dict = Depends(require_admin),
):
    """List all orders (admin only), newest first, with optional status filter."""
    query = select(Order)
    if status_filter:
        query = query.where(Order.status == status_filter)

    total = (
        await db.execute(select(func.count()).select_from(query.subquery()))
    ).scalar() or 0

    query = query.order_by(Order.created_at.desc()).offset(offset).limit(limit)
    items = (await db.execute(query)).scalars().all()
    return OrderList(items=items, total=total)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: uuid.UUID,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get one order (admin or owning buyer). Used for buyer payment polling."""
    order = await _load_order_or_404(db, order_id)
    _assert_order_access(order, current_user)
    response.headers["Cache-Control"] = "no-store"
    return order


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: uuid.UUID,
    payload: OrderStatusUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    admin_user: dict = Depends(require_admin),
):
    """Owner-driven fulfillment transition (dispatch / deliver / cancel)."""
    order = await _load_order_or_404(db, order_id)
    try:
        order = await orders.transition_order(
            db,
            order,
            payload.status,
            eta_minutes=payload.eta_minutes,
            dispatch_at=payload.dispatch_at,
        )
    except InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    # Notify the buyer of every meaningful status change.
    if payload.status == "paid":
        background_tasks.add_task(notifications.send_buyer_invoice, order.id)
    elif payload.status in ("preparing", "dispatched", "delivered", "cancelled", "payment_expired"):
        background_tasks.add_task(
            notifications.send_buyer_status_update, order.id, payload.status
        )
    return order


@router.post("/{order_id}/payment/refresh", response_model=OrderResponse)
async def refresh_payment(
    order_id: uuid.UUID,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Buyer/owner manual fallback when an ABA callback was missed. In stub mode this
    just returns the current state; in live mode this is where a PayWay status
    re-query would run. Webhook remains the source of truth.
    """
    order = await _load_order_or_404(db, order_id)
    _assert_order_access(order, current_user)
    response.headers["Cache-Control"] = "no-store"
    return order
