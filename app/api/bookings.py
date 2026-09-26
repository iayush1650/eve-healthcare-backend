"""Booking API routes — create, list, get, cancel bookings."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.schemas.booking import (
    BookingCancelRequest,
    BookingCreateRequest,
    BookingListResponse,
    BookingResponse,
)
from app.services.booking import BookingService

settings = get_settings()
router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post(
    "/",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new booking",
    description="Book a diagnostic test at a centre. Requires authentication.",
)
def create_booking(
    data: BookingCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a booking for the authenticated user."""
    service = BookingService(db)
    booking = service.create_booking(current_user, data)
    return _build_booking_response(booking)


@router.get(
    "/",
    response_model=BookingListResponse,
    summary="List my bookings",
    description="Retrieve paginated bookings for the authenticated user.",
)
def list_bookings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all bookings for the current user."""
    service = BookingService(db)
    bookings, total = service.list_user_bookings(current_user, page, page_size)

    return BookingListResponse(
        bookings=[_build_booking_response(b) for b in bookings],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{booking_id}",
    response_model=BookingResponse,
    summary="Get booking details",
)
def get_booking(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve details of a specific booking."""
    service = BookingService(db)
    booking = service.get_booking(booking_id, current_user)
    return _build_booking_response(booking)


@router.post(
    "/{booking_id}/cancel",
    response_model=BookingResponse,
    summary="Cancel a booking",
    description="Cancel a PENDING or CONFIRMED booking.",
)
def cancel_booking(
    booking_id: UUID,
    body: BookingCancelRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a booking. Only PENDING/CONFIRMED bookings can be cancelled."""
    service = BookingService(db)
    booking = service.cancel_booking(booking_id, current_user)
    return _build_booking_response(booking)


def _build_booking_response(booking) -> BookingResponse:
    """Build BookingResponse from a Booking model instance."""
    return BookingResponse(
        id=booking.id,
        user_id=booking.user_id,
        centre_test_id=booking.centre_test_id,
        centre_name=booking.centre_test.centre.name,
        test_name=booking.centre_test.test.name,
        appointment_datetime=booking.appointment_datetime,
        amount=booking.amount,
        status=booking.status,
        created_at=booking.created_at,
        updated_at=booking.updated_at,
    )
