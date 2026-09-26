"""Pydantic schemas for payments and webhooks."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.payment import PaymentStatus


# ── Request Schemas ──────────────────────────────────────────────────────────

class PaymentCreateRequest(BaseModel):
    """Schema for initiating a simulated payment."""

    booking_id: UUID
    payment_method: str = Field(default="SIMULATED", max_length=50)


class WebhookPayload(BaseModel):
    """Schema for incoming webhook events from the simulated payment provider.

    The event_id field is critical for idempotency — duplicate events
    with the same event_id will be safely ignored.
    """

    event_id: str = Field(..., min_length=1, max_length=255)
    event_type: str = Field(..., min_length=1, max_length=100)
    transaction_id: str = Field(..., min_length=1, max_length=255)
    status: PaymentStatus
    amount: Decimal = Field(..., gt=0)
    timestamp: datetime | None = None


# ── Response Schemas ─────────────────────────────────────────────────────────

class PaymentResponse(BaseModel):
    """Payment data."""

    id: UUID
    booking_id: UUID
    transaction_id: str
    amount: Decimal
    status: PaymentStatus
    payment_method: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WebhookResponse(BaseModel):
    """Response after processing a webhook event."""

    status: str
    message: str
    event_id: str
