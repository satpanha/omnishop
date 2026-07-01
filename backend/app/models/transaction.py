"""
Transaction model – records of buyer purchases.

Supports buyers from both Telegram and Instagram platforms.
Status follows a simple lifecycle: pending → paid | cancelled.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.product import Product


class Transaction(Base):
    __tablename__ = "transaction"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
    )

    order_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("order.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Parent Order (line item). Nullable only during the backfill window.",
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("product.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    buyer_platform: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Platform of the buyer: 'telegram' or 'instagram'",
    )
    buyer_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Platform-specific buyer identifier",
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="Order status: 'pending', 'paid', or 'cancelled'",
    )

    # ── Relationships ─────────────────────────────────────────
    order: Mapped[Order | None] = relationship(
        "Order",
        back_populates="line_items",
    )
    product: Mapped[Product] = relationship(
        "Product",
        back_populates="transactions",
    )

    def __repr__(self) -> str:
        return f"<Transaction {self.id} status={self.status}>"
