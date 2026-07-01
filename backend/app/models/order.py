"""
Order model – the payable aggregate root for a checkout.

An Order groups one or more :class:`Transaction` line items into a single unit
that carries the payment, the delivery information, and the fulfillment
lifecycle. It was introduced by the "OmniBot" conversational-checkout feature;
before it, each cart item was its own standalone Transaction with no grouping.

Lifecycle (see ``app.services.order_state``):
    awaiting_payment → paid → preparing → dispatched → delivered
    (side exits: cancelled, payment_expired)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.payment import Payment
    from app.models.seller import Seller
    from app.models.transaction import Transaction


# Allowed order statuses (kept in sync with app.services.order_state.ORDER_TRANSITIONS).
ORDER_STATUSES = (
    "awaiting_payment",
    "paid",
    "preparing",
    "dispatched",
    "delivered",
    "cancelled",
    "payment_expired",
)


class Order(Base):
    __tablename__ = "order"
    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="order_total_non_negative"),
        CheckConstraint(
            "status IN ("
            "'awaiting_payment','paid','preparing','dispatched',"
            "'delivered','cancelled','payment_expired')",
            name="order_status_valid",
        ),
    )

    seller_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("seller.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    buyer_platform: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="telegram",
        comment="Platform of the buyer: 'telegram' or 'instagram'",
    )
    buyer_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Platform-specific buyer identifier (Telegram user id)",
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="USD",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="awaiting_payment",
        index=True,
    )

    # ── Delivery (sensitive: geolocation PII) ─────────────────
    delivery_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    delivery_lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    distance_km: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    eta_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dispatch_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Idempotency ───────────────────────────────────────────
    idempotency_key: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
        comment="Client-supplied key to dedupe double-submitted checkouts",
    )

    # ── Relationships ─────────────────────────────────────────
    seller: Mapped[Seller] = relationship("Seller", back_populates="orders")
    line_items: Mapped[list[Transaction]] = relationship(
        "Transaction",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    payment: Mapped[Payment | None] = relationship(
        "Payment",
        back_populates="order",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Order {self.id} status={self.status} total={self.total_amount}>"
