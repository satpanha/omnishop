"""
Conversations API endpoints (admin/owner only).

The owner's primary surface is Telegram itself, but these endpoints back the web
admin: list buyer threads, read history, and send a reply to a buyer.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.models.conversation import Conversation
from app.schemas.conversation import (
    ConversationDetail,
    ConversationList,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)
from app.services import conversations as conv_service

router = APIRouter()


@router.get("", response_model=ConversationList)
async def list_conversations(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    admin_user: dict = Depends(require_admin),
):
    """List buyer conversations, most recently active first (admin only)."""
    query = select(Conversation)
    total = (
        await db.execute(select(func.count()).select_from(query.subquery()))
    ).scalar() or 0
    query = (
        query.order_by(Conversation.last_message_at.desc().nullslast())
        .offset(offset)
        .limit(limit)
    )
    items = (await db.execute(query)).scalars().all()
    return ConversationList(items=items, total=total)


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: dict = Depends(require_admin),
):
    """Read a conversation and its full message history (admin only)."""
    conv = (
        await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
    ).scalar_one_or_none()
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return conv


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: dict = Depends(require_admin),
):
    """Owner sends a message to the buyer (web-admin parity with the bot)."""
    conv = (
        await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
    ).scalar_one_or_none()
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")

    msg, delivered = await conv_service.send_owner_message(db, conv, payload.text)
    if not delivered:
        # Persisted, but transport failed (e.g. buyer blocked the bot).
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Message saved but could not be delivered to the buyer.",
        )
    return msg
