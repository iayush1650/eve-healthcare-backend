"""Authentication API routes — signup and login."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.user import (
    TokenResponse,
    UserLoginRequest,
    UserResponse,
    UserSignupRequest,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account and return a JWT token.",
)
def signup(data: UserSignupRequest, db: Session = Depends(get_db)):
    """Register a new user and return an access token."""
    service = AuthService(db)
    user, token = service.signup(data)
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login",
    description="Authenticate with email and password to receive a JWT token.",
)
def login(data: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return an access token."""
    service = AuthService(db)
    user, token = service.login(data)
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )
