"""Diagnostic Test and CentreTest (junction) models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class DiagnosticTest(Base):
    """Represents a type of diagnostic test (e.g., Blood Test, MRI)."""

    __tablename__ = "diagnostic_tests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True, index=True)
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
    centre_tests = relationship(
        "CentreTest", back_populates="test", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<DiagnosticTest(id={self.id}, name={self.name})>"


class CentreTest(Base):
    """Junction table linking centres to tests with pricing.

    Each centre can offer the same test at a different price.
    """

    __tablename__ = "centre_tests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    centre_id = Column(
        UUID(as_uuid=True),
        ForeignKey("diagnostic_centres.id", ondelete="CASCADE"),
        nullable=False,
    )
    test_id = Column(
        UUID(as_uuid=True),
        ForeignKey("diagnostic_tests.id", ondelete="CASCADE"),
        nullable=False,
    )
    price = Column(Numeric(10, 2), nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Unique constraint: a centre can list a specific test only once
    __table_args__ = (
        UniqueConstraint("centre_id", "test_id", name="uq_centre_test"),
    )

    # Relationships
    centre = relationship("DiagnosticCentre", back_populates="centre_tests")
    test = relationship("DiagnosticTest", back_populates="centre_tests")
    bookings = relationship("Booking", back_populates="centre_test", lazy="selectin")

    def __repr__(self) -> str:
        return f"<CentreTest(centre={self.centre_id}, test={self.test_id}, price={self.price})>"
