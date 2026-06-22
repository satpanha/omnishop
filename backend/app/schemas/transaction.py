"""
Pydantic v2 schemas for transaction operations.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TransactionCreate(BaseModel):
    """Schema for creating a new transaction (buyer placing an order)."""
    product_id: uuid.UUID
    quantity: int = Field(..., ge=1, description="Must order at least 1 item")


class TransactionStatusUpdate(BaseModel):
    """Schema for updating transaction status (admin action)."""
    status: Literal["pending", "paid", "cancelled"]


class TransactionResponse(BaseModel):
    """Full transaction representation returned from the API."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    buyer_platform: str
    buyer_id: str
    quantity: int
    total_price: Decimal
    status: str
    created_at: datetime
    updated_at: datetime


class TransactionList(BaseModel):
    """Paginated list of transactions."""
    items: list[TransactionResponse]
    total: int
