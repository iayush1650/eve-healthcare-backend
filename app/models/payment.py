"""Payment and WebhookEvent models."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class PaymentStatus(str, enum.Enum):
    """Possible states for a payment."""

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Payment(Base):
    """Represents a payment associated with a booking."""

    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One payment per booking
        index=True,
    )
    transaction_id = Column(
        String(255), unique=True, nullable=False, index=True
    )
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(
        Enum(PaymentStatus),
        default=PaymentStatus.PENDING,
        nullable=False,
    )
    payment_method = Column(String(50), default="SIMULATED", nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    booking = relationship("Booking", back_populates="payment")

    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, txn={self.transaction_id}, status={self.status})>"


class WebhookEvent(Base):
    """Tracks processed webhook events for idempotency.

    Stores every unique event_id received from the payment provider
    so that duplicate deliveries are safely ignored.
    """

    __tablename__ = "webhook_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(String(255), unique=True, nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=True)
    processed = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<WebhookEvent(event_id={self.event_id}, processed={self.processed})>"
