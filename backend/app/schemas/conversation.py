"""
Pydantic v2 schemas for conversation / messaging.
"""

import uuid
from datetime import datetime

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ConversationStateUpdate(BaseModel):
    """Schema to update the conversation state (e.g. resolve/close or return to bot)."""
    state: Literal["bot", "awaiting_owner", "owner_handling", "closed"]


class MessageCreate(BaseModel):
    """Owner sends a message to a buyer (web-admin parity with the bot button)."""

    text: str = Field(..., min_length=1, max_length=4096)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    direction: str
    sender: str
    text: str
    created_at: datetime


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    buyer_platform: str
    buyer_id: str
    state: str
    last_message_at: datetime | None
    created_at: datetime


class ConversationDetail(ConversationResponse):
    messages: list[MessageResponse]


class ConversationList(BaseModel):
    items: list[ConversationResponse]
    total: int
