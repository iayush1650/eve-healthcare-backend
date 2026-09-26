"""Pydantic schemas for diagnostic centres."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


# ── Request Schemas ──────────────────────────────────────────────────────────

class CentreCreateRequest(BaseModel):
    """Schema for creating a diagnostic centre."""

    name: str = Field(..., min_length=2, max_length=255)
    location: str = Field(..., min_length=2, max_length=255)
    address: str | None = None
    phone: str | None = Field(None, max_length=20)


# ── Response Schemas ─────────────────────────────────────────────────────────

class TestInCentreResponse(BaseModel):
    """A test offered at a centre, with pricing."""

    centre_test_id: UUID
    test_id: UUID
    test_name: str
    category: str | None
    price: Decimal
    is_available: bool

    model_config = {"from_attributes": True}


class CentreResponse(BaseModel):
    """Diagnostic centre public data."""

    id: UUID
    name: str
    location: str
    address: str | None
    phone: str | None
    is_active: bool
    created_at: datetime
    tests: list[TestInCentreResponse] = []

    model_config = {"from_attributes": True}


class CentreListResponse(BaseModel):
    """Paginated list of diagnostic centres."""

    centres: list[CentreResponse]
    total: int
    page: int
    page_size: int
