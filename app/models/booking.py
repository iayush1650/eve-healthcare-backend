"""Booking model with status tracking."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class BookingStatus(str, enum.Enum):
    """Possible states for a booking."""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Booking(Base):
    """Represents a user's booking for a diagnostic test at a centre."""

    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    centre_test_id = Column(
        UUID(as_uuid=True),
        ForeignKey("centre_tests.id", ondelete="CASCADE"),
        nullable=False,
    )
    appointment_datetime = Column(DateTime(timezone=True), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(
        Enum(BookingStatus),
        default=BookingStatus.PENDING,
        nullable=False,
        index=True,
    )
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
    user = relationship("User", back_populates="bookings")
    centre_test = relationship("CentreTest", back_populates="bookings")
    payment = relationship(
        "Payment", back_populates="booking", uselist=False, lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Booking(id={self.id}, status={self.status})>"
