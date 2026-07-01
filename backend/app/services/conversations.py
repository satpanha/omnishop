"""
Conversation / messaging service.

Owns the buyer↔bot↔owner thread: persisting messages, running the auto-responder
for tier-1 questions, escalating to the owner when the bot can't help, and
relaying the owner's replies back to the buyer. Transport (Telegram/Instagram) is
isolated in :func:`_deliver_to_buyer`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message
from app.services.auto_responder import find_response
from app.services.instagram import InstagramService
from app.services.telegram import TelegramService

logger = logging.getLogger(__name__)


@dataclass
class InboundResult:
    conversation_id: str
    reply: str | None  # auto-response to send back to the buyer, if any
    escalated: bool  # True → owner should be notified, bot had no answer


async def get_or_create_conversation(
    db: AsyncSession, platform: str, buyer_id: str | int
) -> Conversation:
    """Fetch (or create) the single conversation for a buyer on a platform."""
    buyer_id = str(buyer_id)
    stmt = select(Conversation).where(
        Conversation.buyer_platform == platform,
        Conversation.buyer_id == buyer_id,
    )
    conv = (await db.execute(stmt)).scalar_one_or_none()
    if conv is None:
        conv = Conversation(buyer_platform=platform, buyer_id=buyer_id, state="bot")
        db.add(conv)
        await db.flush()
    return conv


async def record_message(
    db: AsyncSession,
    conv: Conversation,
    *,
    direction: str,
    sender: str,
    text: str,
    telegram_message_id: str | None = None,
) -> Message:
    """Append a message to a conversation and bump ``last_message_at``."""
    msg = Message(
        conversation_id=conv.id,
        direction=direction,
        sender=sender,
        text=text,
        telegram_message_id=telegram_message_id,
    )
    db.add(msg)
    conv.last_message_at = datetime.now(timezone.utc)
    await db.flush()
    return msg


async def handle_inbound_message(
    db: AsyncSession, platform: str, buyer_id: str | int, text: str
) -> InboundResult:
    """
    Record an inbound buyer message and decide the response:
      * if the owner is actively handling, do NOT auto-reply — escalate so the
        owner sees the new message;
      * else try the auto-responder; on a hit, record + return the reply;
      * on a miss, escalate (state → awaiting_owner).
    Does not send anything itself — the caller owns transport (matches the
    existing webhook pattern).
    """
    conv = await get_or_create_conversation(db, platform, buyer_id)
    await record_message(db, conv, direction="inbound", sender="buyer", text=text)

    if conv.state == "owner_handling":
        await db.commit()
        return InboundResult(str(conv.id), reply=None, escalated=True)

    reply = await find_response(db, text)
    if reply:
        if conv.state == "closed":
            conv.state = "bot"
        await record_message(db, conv, direction="outbound", sender="bot", text=reply)
        await db.commit()
        return InboundResult(str(conv.id), reply=reply, escalated=False)

    # No auto-answer → escalate to the owner.
    conv.state = "awaiting_owner"
    await db.commit()
    return InboundResult(str(conv.id), reply=None, escalated=True)


async def send_owner_message(
    db: AsyncSession, conv: Conversation, text: str
) -> tuple[Message, bool]:
    """
    Owner → buyer. Records the outbound message, marks the conversation as
    owner-handled, and delivers it over the buyer's platform.

    Returns (recorded_message, delivered).
    """
    msg = await record_message(db, conv, direction="outbound", sender="owner", text=text)
    conv.state = "owner_handling"
    await db.commit()
    delivered = await _deliver_to_buyer(conv.buyer_platform, conv.buyer_id, text)
    return msg, delivered


async def _deliver_to_buyer(platform: str, buyer_id: str, text: str) -> bool:
    """Send text to a buyer over the correct transport."""
    if platform == "instagram":
        ig = InstagramService()
        try:
            return await ig.send_reply(recipient_id=buyer_id, text=text)
        finally:
            await ig.close()
    tg = TelegramService()
    try:
        return await tg.send_message(chat_id=buyer_id, text=text)
    finally:
        await tg.close()
