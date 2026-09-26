"""Booking service — create, list, cancel bookings."""

from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy.orm import Session

from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.models.booking import Booking, BookingStatus
from app.models.test import CentreTest
from app.models.user import User
from app.schemas.booking import BookingCreateRequest

logger = structlog.get_logger(__name__)


class BookingService:
    """Handles booking lifecycle operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_booking(self, user: User, data: BookingCreateRequest) -> Booking:
        """Create a new diagnostic test booking.

        Validates:
        - Centre test exists and is available
        - Appointment is in the future

        Returns the created Booking.
        """
        # Validate centre-test exists and is available
        centre_test = (
            self.db.query(CentreTest)
            .filter(CentreTest.id == data.centre_test_id)
            .first()
        )
        if not centre_test:
            raise NotFoundException(detail="Diagnostic test offering not found")

        if not centre_test.is_available:
            raise BadRequestException(
                detail="This test is currently not available at the selected centre"
            )

        if not centre_test.centre.is_active:
            raise BadRequestException(
                detail="The selected diagnostic centre is currently inactive"
            )

        booking = Booking(
            user_id=user.id,
            centre_test_id=centre_test.id,
            appointment_datetime=data.appointment_datetime,
            amount=centre_test.price,
            status=BookingStatus.PENDING,
        )
        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)

        logger.info(
            "booking_created",
            booking_id=str(booking.id),
            user_id=str(user.id),
            amount=str(booking.amount),
        )
        return booking

    def get_booking(self, booking_id: UUID, user: User) -> Booking:
        """Retrieve a booking by ID, ensuring it belongs to the user.

        Raises:
            NotFoundException: If booking doesn't exist.
            ForbiddenException: If booking belongs to another user.
        """
        booking = self.db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise NotFoundException(detail="Booking not found")

        if booking.user_id != user.id:
            raise ForbiddenException(
                detail="You are not authorized to view this booking"
            )

        return booking

    def list_user_bookings(
        self, user: User, page: int = 1, page_size: int = 20
    ) -> tuple[list[Booking], int]:
        """List all bookings for a user with pagination."""
        query = self.db.query(Booking).filter(Booking.user_id == user.id)
        total = query.count()
        bookings = (
            query.order_by(Booking.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return bookings, total

    def cancel_booking(self, booking_id: UUID, user: User) -> Booking:
        """Cancel a pending booking.

        Only PENDING bookings can be cancelled. CONFIRMED bookings
        would need a refund flow in production.

        Raises:
            NotFoundException: If booking doesn't exist.
            ForbiddenException: If booking belongs to another user.
            BadRequestException: If booking is not in PENDING state.
        """
        booking = self.get_booking(booking_id, user)

        if booking.status not in (BookingStatus.PENDING, BookingStatus.CONFIRMED):
            raise BadRequestException(
                detail=f"Cannot cancel a booking with status '{booking.status.value}'"
            )

        booking.status = BookingStatus.CANCELLED
        booking.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(booking)

        logger.info("booking_cancelled", booking_id=str(booking.id))
        return booking
