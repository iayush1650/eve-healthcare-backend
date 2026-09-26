"""Authentication service — signup, login, token validation."""

import structlog
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException, ConflictException, UnauthorizedException
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserSignupRequest, UserLoginRequest

logger = structlog.get_logger(__name__)


class AuthService:
    """Handles user authentication operations."""

    def __init__(self, db: Session):
        self.db = db

    def signup(self, data: UserSignupRequest) -> tuple[User, str]:
        """Register a new user and return user + JWT token.

        Raises:
            ConflictException: If email is already registered.
        """
        # Check for existing user
        existing = self.db.query(User).filter(User.email == data.email).first()
        if existing:
            logger.warning("signup_duplicate_email", email=data.email)
            raise ConflictException(detail="A user with this email already exists")

        # Create user
        user = User(
            email=data.email,
            full_name=data.full_name,
            phone=data.phone,
            password_hash=hash_password(data.password),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        token = create_access_token(data={"sub": str(user.id)})
        logger.info("user_registered", user_id=str(user.id), email=user.email)
        return user, token

    def login(self, data: UserLoginRequest) -> tuple[User, str]:
        """Authenticate user and return user + JWT token.

        Raises:
            UnauthorizedException: If credentials are invalid.
        """
        user = self.db.query(User).filter(User.email == data.email).first()
        if not user or not verify_password(data.password, user.password_hash):
            logger.warning("login_failed", email=data.email)
            raise UnauthorizedException(detail="Invalid email or password")

        if not user.is_active:
            logger.warning("login_inactive_user", user_id=str(user.id))
            raise UnauthorizedException(detail="User account is deactivated")

        token = create_access_token(data={"sub": str(user.id)})
        logger.info("user_logged_in", user_id=str(user.id))
        return user, token
