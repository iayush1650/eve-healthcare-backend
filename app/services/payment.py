"""Payment service — simulated payment processing and idempotent webhooks."""

import random
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy.orm import Session

from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from app.models.booking import Booking, BookingStatus
from app.models.payment import Payment, PaymentStatus, WebhookEvent
from app.schemas.payment import PaymentCreateRequest, WebhookPayload

logger = structlog.get_logger(__name__)


class PaymentService:
    """Handles simulated payment processing and webhook events."""

    def __init__(self, db: Session):
        self.db = db

    def process_payment(self, booking_id: uuid.UUID, user_id: uuid.UUID) -> Payment:
        """Simulate a payment for a booking.

        The payment randomly results in SUCCESS or FAILED (70/30 split).
        Updates the related booking status accordingly.

        Raises:
            NotFoundException: If booking doesn't exist.
            BadRequestException: If booking is not in PENDING state
                                 or already has a payment.
        """
        # Validate booking
        booking = self.db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise NotFoundException(detail="Booking not found")

        if booking.user_id != user_id:
            raise BadRequestException(
                detail="You are not authorized to pay for this booking"
            )

        if booking.status != BookingStatus.PENDING:
            raise BadRequestException(
                detail=f"Cannot process payment for booking with status '{booking.status.value}'"
            )

        # Check for existing payment
        existing_payment = (
            self.db.query(Payment).filter(Payment.booking_id == booking_id).first()
        )
        if existing_payment:
            raise ConflictException(
                detail="Payment already exists for this booking"
            )

        # Simulate payment outcome (70% success, 30% failure)
        simulated_status = random.choices(
            [PaymentStatus.SUCCESS, PaymentStatus.FAILED],
            weights=[70, 30],
            k=1,
        )[0]

        # Generate a unique transaction ID
        transaction_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"

        # Create payment record
        payment = Payment(
            booking_id=booking_id,
            transaction_id=transaction_id,
            amount=booking.amount,
            status=simulated_status,
            payment_method="SIMULATED",
        )
        self.db.add(payment)

        # Update booking status based on payment result
        if simulated_status == PaymentStatus.SUCCESS:
            booking.status = BookingStatus.CONFIRMED
        else:
            booking.status = BookingStatus.FAILED

        booking.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(payment)

        logger.info(
            "payment_processed",
            payment_id=str(payment.id),
            transaction_id=transaction_id,
            booking_id=str(booking_id),
            status=simulated_status.value,
        )
        return payment

    def process_webhook(self, payload: WebhookPayload) -> dict:
        """Process an incoming payment webhook event idempotently.

        Uses the event_id to ensure duplicate webhook deliveries
        are safely ignored without corrupting data.

        Returns a status dict indicating the processing result.
        """
        # ── Idempotency check ────────────────────────────────────────────
        existing_event = (
            self.db.query(WebhookEvent)
            .filter(WebhookEvent.event_id == payload.event_id)
            .first()
        )
        if existing_event:
            logger.info(
                "webhook_duplicate_ignored",
                event_id=payload.event_id,
                processed=existing_event.processed,
            )
            return {
                "status": "duplicate",
                "message": "Event already processed",
                "event_id": payload.event_id,
            }

        # ── Record the event first (before processing) ───────────────────
        webhook_event = WebhookEvent(
            event_id=payload.event_id,
            event_type=payload.event_type,
            payload=payload.model_dump(mode="json"),
            processed=False,
        )
        self.db.add(webhook_event)
        self.db.flush()  # Flush to catch unique constraint violations early

        # ── Find the payment by transaction ID ───────────────────────────
        payment = (
            self.db.query(Payment)
            .filter(Payment.transaction_id == payload.transaction_id)
            .first()
        )
        if not payment:
            # Log but don't fail — might be an event for a txn we don't know about
            webhook_event.processed = True
            self.db.commit()
            logger.warning(
                "webhook_unknown_transaction",
                event_id=payload.event_id,
                transaction_id=payload.transaction_id,
            )
            return {
                "status": "ignored",
                "message": "Transaction not found",
                "event_id": payload.event_id,
            }

        # ── Update payment and booking status ────────────────────────────
        payment.status = payload.status
        payment.updated_at = datetime.now(timezone.utc)

        booking = payment.booking
        if payload.status == PaymentStatus.SUCCESS:
            booking.status = BookingStatus.CONFIRMED
        elif payload.status == PaymentStatus.FAILED:
            booking.status = BookingStatus.FAILED

        booking.updated_at = datetime.now(timezone.utc)
        webhook_event.processed = True

        self.db.commit()

        logger.info(
            "webhook_processed",
            event_id=payload.event_id,
            transaction_id=payload.transaction_id,
            payment_status=payload.status.value,
            booking_status=booking.status.value,
        )
        return {
            "status": "processed",
            "message": "Payment status updated successfully",
            "event_id": payload.event_id,
        }

    def get_payment_by_booking(self, booking_id: uuid.UUID) -> Payment | None:
        """Retrieve payment for a booking."""
        return (
            self.db.query(Payment).filter(Payment.booking_id == booking_id).first()
        )
