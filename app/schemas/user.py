"""Pydantic schemas for user authentication."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ── Request Schemas ──────────────────────────────────────────────────────────

class UserSignupRequest(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: str | None = Field(None, max_length=20)
    password: str = Field(..., min_length=8, max_length=128)


class UserLoginRequest(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str


# ── Response Schemas ─────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    """Public user profile data."""

    id: UUID
    email: str
    full_name: str
    phone: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """JWT token response after login/signup."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse
