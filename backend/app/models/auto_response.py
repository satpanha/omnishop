"""
AutoResponse model – keyword → response mappings for the auto-responder.

If seller_id is NULL the response is considered global (matches any seller).
Keywords are stored lowercase for case-insensitive matching.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.seller import Seller


class AutoResponse(Base):
    __tablename__ = "auto_response"

    seller_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("seller.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="NULL = global response, otherwise seller-scoped",
    )
    keyword: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Lowercase keyword to match against incoming messages",
    )
    response_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Response template; may contain {product_name}, {price}, {stock}",
    )

    # ── Relationships ─────────────────────────────────────────
    seller: Mapped[Seller | None] = relationship(
        "Seller",
        back_populates="auto_responses",
    )

    def __repr__(self) -> str:
        return f"<AutoResponse keyword={self.keyword!r}>"
