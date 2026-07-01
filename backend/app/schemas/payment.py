"""
Pydantic v2 schemas for payment representation.

Note: ``provider_txn_ref`` and ``raw_callback`` are intentionally NOT exposed on
the buyer-facing response — only what's needed to render the QR / pay link.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PaymentResponse(BaseModel):
    """Buyer-facing payment view: enough to render the QR + pay button."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: str
    amount: Decimal
    currency: str
    khqr_string: str | None
    aba_link: str | None
    status: str
    paid_at: datetime | None
