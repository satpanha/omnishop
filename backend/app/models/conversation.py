"""
Conversation and Message models – buyer ↔ bot ↔ owner messaging.

A Conversation is the bot↔buyer thread for a single buyer on a single platform.
It carries a small state machine so a message can start with the auto-responder
(``bot``), escalate to the owner (``awaiting_owner`` → ``owner_handling``) and be
closed. Each inbound/outbound Message is persisted append-only for audit and so
the owner can see history.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

CONVERSATION_STATES = ("bot", "awaiting_owner", "owner_handling", "closed")
MESSAGE_DIRECTIONS = ("inbound", "outbound")
MESSAGE_SENDERS = ("buyer", "owner", "bot")


class Conversation(Base):
    __tablename__ = "conversation"
    __table_args__ = (
        UniqueConstraint(
            "buyer_platform", "buyer_id", name="conversation_platform_buyer"
        ),
        CheckConstraint(
            "state IN ('bot','awaiting_owner','owner_handling','closed')",
            name="conversation_state_valid",
        ),
    )

    buyer_platform: Mapped[str] = mapped_column(String(20), nullable=False)
    buyer_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="bot",
    )
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # ── Relationships ─────────────────────────────────────────
    messages: Mapped[list[Message]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Message.created_at",
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.id} buyer={self.buyer_id} state={self.state}>"


class Message(Base):
    __tablename__ = "message"
    __table_args__ = (
        CheckConstraint(
            "direction IN ('inbound','outbound')", name="message_direction_valid"
        ),
        CheckConstraint(
            "sender IN ('buyer','owner','bot')", name="message_sender_valid"
        ),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversation.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    sender: Mapped[str] = mapped_column(String(10), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    telegram_message_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ── Relationships ─────────────────────────────────────────
    conversation: Mapped[Conversation] = relationship(
        "Conversation",
        back_populates="messages",
    )

    def __repr__(self) -> str:
        return f"<Message {self.id} {self.direction} sender={self.sender}>"
