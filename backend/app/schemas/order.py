"""
Pydantic v2 schemas for order operations.

An Order groups one or more line items (Transactions) into a single payable unit
with delivery info and a fulfillment lifecycle.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.payment import PaymentResponse


class OrderLineItemCreate(BaseModel):
    """One product line in a checkout."""

    product_id: uuid.UUID
    quantity: int = Field(..., ge=1, description="Must order at least 1 item")


class DeliveryInfo(BaseModel):
    """Buyer delivery location. lat/lng optional — order is allowed without it."""

    lat: Decimal | None = Field(default=None, ge=-90, le=90)
    lng: Decimal | None = Field(default=None, ge=-180, le=180)
    address: str | None = Field(default=None, max_length=500)


class OrderCreate(BaseModel):
    """Create an order from a cart (replaces the per-item POST /transactions loop)."""

    items: list[OrderLineItemCreate] = Field(..., min_length=1)
    delivery: DeliveryInfo | None = None
    idempotency_key: str | None = Field(default=None, max_length=64)


class OrderStatusUpdate(BaseModel):
    """Admin transition of an order's fulfillment status."""

    status: Literal[
        "awaiting_payment",
        "paid",
        "preparing",
        "dispatched",
        "delivered",
        "cancelled",
        "payment_expired",
    ]
    eta_minutes: int | None = Field(default=None, ge=0)
    dispatch_at: datetime | None = None


class OrderLineItemResponse(BaseModel):
    """A line item within an order."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    total_price: Decimal


class OrderResponse(BaseModel):
    """Full order representation: lines + payment + delivery + lifecycle."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    seller_id: uuid.UUID
    buyer_platform: str
    buyer_id: str
    total_amount: Decimal
    currency: str
    status: str
    delivery_address: str | None
    delivery_lat: Decimal | None
    delivery_lng: Decimal | None
    distance_km: Decimal | None
    eta_minutes: int | None
    dispatch_at: datetime | None
    created_at: datetime
    updated_at: datetime
    line_items: list[OrderLineItemResponse]
    payment: PaymentResponse | None


class OrderList(BaseModel):
    """Paginated list of orders."""

    items: list[OrderResponse]
    total: int
