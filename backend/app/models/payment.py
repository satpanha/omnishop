"""
Payment model – one payment attempt per :class:`Order`.

The payment record is the **source of truth** for whether an order is paid.
Its status is only ever advanced to ``paid`` by the ABA PayWay server-to-server
callback (see ``app.api.v1.webhooks.payway_webhook``) or the reconciliation job
— never by a UI write. ``provider_txn_ref`` is the idempotency anchor for
callbacks; ``raw_callback`` stores the verified provider payload for audit.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.order import Order


PAYMENT_STATUSES = ("initiated", "paid", "failed", "expired")


class Payment(Base):
    __tablename__ = "payment"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="payment_amount_non_negative"),
        CheckConstraint(
            "status IN ('initiated','paid','failed','expired')",
            name="payment_status_valid",
        ),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("order.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="1:1 — each order has at most one payment",
    )
    provider: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="aba_payway",
        comment="Payment provider; enum-extensible (e.g. 'bakong_khqr')",
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    khqr_string: Mapped[str | None] = mapped_column(Text, nullable=True)
    aba_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    provider_txn_ref: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
        index=True,
        comment="Provider transaction reference; idempotency anchor for callbacks",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="initiated",
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    # JSONB on Postgres, generic JSON on SQLite (tests) — sensitive, excluded from logs.
    raw_callback: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
    )

    # ── Relationships ─────────────────────────────────────────
    order: Mapped[Order] = relationship("Order", back_populates="payment")

    def __repr__(self) -> str:
        return f"<Payment {self.id} order={self.order_id} status={self.status}>"
