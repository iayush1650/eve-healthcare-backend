"""Pydantic schemas for bookings."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.booking import BookingStatus


# ── Request Schemas ──────────────────────────────────────────────────────────

class BookingCreateRequest(BaseModel):
    """Schema for creating a booking."""

    centre_test_id: UUID
    appointment_datetime: datetime

    @field_validator("appointment_datetime")
    @classmethod
    def validate_future_datetime(cls, v: datetime) -> datetime:
        """Ensure the appointment is in the future."""
        from datetime import timezone

        if v.tzinfo is None:
            from datetime import timezone as tz
            v = v.replace(tzinfo=tz.utc)
        if v <= datetime.now(timezone.utc):
            raise ValueError("Appointment date/time must be in the future")
        return v


class BookingCancelRequest(BaseModel):
    """Schema for cancelling a booking."""

    reason: str | None = None


# ── Response Schemas ─────────────────────────────────────────────────────────

class BookingResponse(BaseModel):
    """Booking data with related information."""

    id: UUID
    user_id: UUID
    centre_test_id: UUID
    centre_name: str
    test_name: str
    appointment_datetime: datetime
    amount: Decimal
    status: BookingStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BookingListResponse(BaseModel):
    """Paginated list of bookings."""

    bookings: list[BookingResponse]
    total: int
    page: int
    page_size: int
