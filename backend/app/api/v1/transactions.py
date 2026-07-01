"""
Transactions API endpoints.
"""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.deps import get_db, require_admin, get_current_user
from app.config import get_settings
from app.models.product import Product
from app.models.transaction import Transaction
from app.schemas.order import OrderLineItemCreate
from app.schemas.transaction import TransactionCreate, TransactionStatusUpdate, TransactionResponse, TransactionList
from app.services import notifications, orders

router = APIRouter()


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    payload: TransactionCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    DEPRECATED — use ``POST /orders`` instead.

    Kept for backward compatibility: wraps a single product into a one-line Order
    (so stock, totals, and notifications all flow through the new aggregate) and
    returns the created line item in the legacy Transaction shape.
    """
    try:
        order = await orders.create_order(
            db,
            buyer_platform="telegram",
            buyer_id=current_user["sub"],
            items=[OrderLineItemCreate(product_id=payload.product_id, quantity=payload.quantity)],
        )
    except orders.OrderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    background_tasks.add_task(notifications.notify_owner_new_order, order.id)
    if get_settings().PAYMENTS_ENABLED and order.payment is not None:
        background_tasks.add_task(notifications.send_buyer_payment_request, order.id)

    # Return the single line item in the legacy Transaction shape.
    return order.line_items[0]


@router.get("", response_model=TransactionList)
async def list_transactions(
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    admin_user: dict = Depends(require_admin),
):
    """List all transactions (Admin only) with optional status filter."""
    query = select(Transaction)
    
    if status_filter:
        query = query.where(Transaction.status == status_filter)

    # Count query
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Get results ordered by created_at desc
    query = query.order_by(Transaction.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    transactions = result.scalars().all()

    return TransactionList(items=transactions, total=total)


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get details of a single transaction by UUID."""
    stmt = select(Transaction).where(Transaction.id == transaction_id)
    result = await db.execute(stmt)
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    # Allow access if requester is Admin OR the buyer of this transaction
    is_admin = current_user.get("role") == "admin"
    is_buyer = transaction.buyer_id == current_user.get("sub")
    
    if not (is_admin or is_buyer):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return transaction


@router.patch("/{transaction_id}/status", response_model=TransactionResponse)
async def update_transaction_status(
    transaction_id: uuid.UUID,
    payload: TransactionStatusUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: dict = Depends(require_admin),
):
    """Update transaction status (Admin only). Returns stock if cancelled."""
    stmt = select(Transaction).where(Transaction.id == transaction_id)
    result = await db.execute(stmt)
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    old_status = transaction.status
    new_status = payload.status

    if old_status == new_status:
        return transaction

    # Handle inventory restocking if cancelling order
    if new_status == "cancelled" and old_status != "cancelled":
        # Restock product
        product_stmt = select(Product).where(Product.id == transaction.product_id)
        product_result = await db.execute(product_stmt)
        product = product_result.scalar_one_or_none()
        if product:
            product.stock_quantity += transaction.quantity
            
    # Handle inventory decrement if reviving a cancelled order
    elif old_status == "cancelled" and new_status != "cancelled":
        product_stmt = select(Product).where(Product.id == transaction.product_id)
        product_result = await db.execute(product_stmt)
        product = product_result.scalar_one_or_none()
        if product:
            if product.stock_quantity < transaction.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot change status. Insufficient product stock to fulfill order. Available: {product.stock_quantity}",
                )
            product.stock_quantity -= transaction.quantity

    transaction.status = new_status
    await db.commit()
    await db.refresh(transaction)
    return transaction
