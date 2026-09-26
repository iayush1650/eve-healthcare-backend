"""Shared API dependencies — database session, current user extraction."""

from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedException
from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User

# Bearer token scheme for Swagger UI support
bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Extract and validate the current user from the JWT token.

    This dependency can be injected into any route that requires
    authentication.

    Raises:
        UnauthorizedException: If token is missing, invalid, or expired.
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise UnauthorizedException(detail="Invalid or expired token")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException(detail="Invalid token payload")

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise UnauthorizedException(detail="Invalid token payload")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UnauthorizedException(detail="User not found")

    if not user.is_active:
        raise UnauthorizedException(detail="User account is deactivated")

    return user
