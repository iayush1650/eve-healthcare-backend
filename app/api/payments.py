"""Payment API routes — simulated payments and webhook handler with async support."""

import structlog
from fastapi import APIRouter, Depends, Query, status
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

logger = structlog.get_logger(__name__)
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
        "event_id will be safely ignored without corrupting data.\n\n"
        "**Async mode**: Set `?async_processing=true` to queue the webhook "
        "for background processing with automatic retry (exponential backoff). "
        "This is recommended for production use."
    ),
)
def payment_webhook(
    payload: WebhookPayload,
    db: Session = Depends(get_db),
    async_processing: bool = Query(
        False,
        description="If true, process webhook asynchronously via Celery with retry",
    ),
):
    """Handle incoming payment webhook events idempotently.

    This endpoint does NOT require authentication as it's called by
    the payment provider. In production, you'd verify a webhook
    signature/secret.

    Supports two processing modes:
    - **Synchronous (default)**: Processes immediately and returns result.
    - **Asynchronous**: Queues to Celery worker with exponential backoff retry.
    """
    if async_processing:
        return _process_webhook_async(payload)

    return _process_webhook_sync(payload, db)


def _process_webhook_sync(payload: WebhookPayload, db: Session) -> WebhookResponse:
    """Process webhook synchronously (original behavior)."""
    service = PaymentService(db)
    result = service.process_webhook(payload)

    return WebhookResponse(
        status=result["status"],
        message=result["message"],
        event_id=result["event_id"],
    )


def _process_webhook_async(payload: WebhookPayload) -> WebhookResponse:
    """Queue webhook for async processing via Celery with retry logic."""
    try:
        from app.tasks.webhook_tasks import process_webhook_async

        task = process_webhook_async.delay(payload.model_dump(mode="json"))
        logger.info(
            "webhook_queued_async",
            event_id=payload.event_id,
            task_id=task.id,
        )
        return WebhookResponse(
            status="queued",
            message=f"Webhook queued for async processing (task_id: {task.id})",
            event_id=payload.event_id,
        )
    except Exception as e:
        # Fallback: if Celery/Redis unavailable, warn and suggest sync mode
        logger.warning(
            "webhook_async_fallback",
            event_id=payload.event_id,
            error=str(e),
        )
        return WebhookResponse(
            status="error",
            message="Async processing unavailable. Use sync mode (remove ?async_processing=true).",
            event_id=payload.event_id,
        )

