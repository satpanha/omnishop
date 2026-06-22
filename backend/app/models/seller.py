"""
Seller model – represents the single shop owner using the TMA.

The seller is identified by their Telegram user ID and optionally linked
to an Instagram Business account for cross-platform messaging.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.auto_response import AutoResponse
    from app.models.product import Product


class Seller(Base):
    __tablename__ = "seller"

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
        comment="Seller's Telegram user ID",
    )
    ig_business_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        comment="Instagram Business account ID (optional)",
    )
    store_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Display name of the store",
    )

    # ── Relationships ─────────────────────────────────────────
    products: Mapped[list[Product]] = relationship(
        "Product",
        back_populates="seller",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    auto_responses: Mapped[list[AutoResponse]] = relationship(
        "AutoResponse",
        back_populates="seller",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Seller {self.store_name!r} tg={self.telegram_id}>"
