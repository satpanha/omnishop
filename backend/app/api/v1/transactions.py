"""
Transactions API endpoints.
"""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.deps import get_db, require_admin, get_current_user
from app.models.product import Product
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionStatusUpdate, TransactionResponse, TransactionList
from app.services.notifications import notify_new_order

router = APIRouter()


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    payload: TransactionCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Create a new transaction (buyer places an order).
    Decrements stock, calculates total price, and triggers an admin notification in the background.
    """
    # 1. Fetch product
    product_stmt = select(Product).where(Product.id == payload.product_id)
    product_result = await db.execute(product_stmt)
    product = product_result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    
    if not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product is currently inactive",
        )

    # 2. Check stock
    if product.stock_quantity < payload.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock. Available: {product.stock_quantity}",
        )

    # 3. Decrement stock
    product.stock_quantity -= payload.quantity

    # 4. Create transaction
    total_price = product.price * payload.quantity
    transaction = Transaction(
        product_id=product.id,
        buyer_platform="telegram",
        buyer_id=current_user["sub"],
        quantity=payload.quantity,
        total_price=total_price,
        status="pending",
    )
    db.add(transaction)
    
    # Commit transaction (which also flushes product stock updates)
    await db.commit()
    await db.refresh(transaction)
    await db.refresh(product)  # to get updated product state for notification

    # 5. Notify admin in background
    background_tasks.add_task(notify_new_order, db, transaction, product)

    return transaction


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
