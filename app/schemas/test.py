"""Pydantic schemas for diagnostic tests."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


# ── Request Schemas ──────────────────────────────────────────────────────────

class TestCreateRequest(BaseModel):
    """Schema for creating a diagnostic test."""

    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    category: str | None = Field(None, max_length=100)


class CentreTestCreateRequest(BaseModel):
    """Schema for linking a test to a centre with pricing."""

    centre_id: UUID
    test_id: UUID
    price: Decimal = Field(..., gt=0, decimal_places=2)


# ── Response Schemas ─────────────────────────────────────────────────────────

class TestResponse(BaseModel):
    """Diagnostic test data."""

    id: UUID
    name: str
    description: str | None
    category: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CentreTestResponse(BaseModel):
    """Test available at a specific centre with pricing."""

    id: UUID
    centre_id: UUID
    centre_name: str
    test_id: UUID
    test_name: str
    price: Decimal
    is_available: bool

    model_config = {"from_attributes": True}


class TestListResponse(BaseModel):
    """Paginated list of tests."""

    tests: list[TestResponse]
    total: int
    page: int
    page_size: int
