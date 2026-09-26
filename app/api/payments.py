"""Payment API routes — simulated payments and webhook handler."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.payment import (
    PaymentCreateRequest,
    PaymentResponse,
    WebhookPayload,
    WebhookResponse,
)
from app.services.payment import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "/",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Process a simulated payment",
    description=(
        "Simulate payment processing for a booking. "
        "The result is randomly SUCCESS (70%) or FAILED (30%). "
        "The related booking status is updated accordingly."
    ),
)
def process_payment(
    data: PaymentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Process a simulated payment for a booking."""
    service = PaymentService(db)
    payment = service.process_payment(data.booking_id, current_user.id)
    return PaymentResponse.model_validate(payment)


@router.post(
    "/webhook/",
    response_model=WebhookResponse,
    summary="Payment webhook endpoint",
    description=(
        "Receives payment status updates from the simulated payment provider. "
        "This endpoint is **idempotent** — duplicate events with the same "
        "event_id will be safely ignored without corrupting data."
    ),
)
def payment_webhook(
    payload: WebhookPayload,
    db: Session = Depends(get_db),
):
    """Handle incoming payment webhook events idempotently.

    This endpoint does NOT require authentication as it's called by
    the payment provider. In production, you'd verify a webhook
    signature/secret.
    """
    service = PaymentService(db)
    result = service.process_webhook(payload)

    return WebhookResponse(
        status=result["status"],
        message=result["message"],
        event_id=result["event_id"],
    )
