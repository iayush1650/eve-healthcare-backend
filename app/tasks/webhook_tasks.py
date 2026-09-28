"""Celery tasks for webhook processing with retry logic.

Implements exponential backoff retry for failed webhook processing,
ensuring reliable delivery even when transient errors occur.
"""

import structlog
from celery import shared_task
from celery.utils.log import get_task_logger

from app.celery_app import celery_app

logger = structlog.get_logger(__name__)
task_logger = get_task_logger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.webhook_tasks.process_webhook_async",
    max_retries=5,
    default_retry_delay=10,
    acks_late=True,
    reject_on_worker_lost=True,
    autoretry_for=(Exception,),
    retry_backoff=True,        # Exponential backoff
    retry_backoff_max=300,     # Max 5 minutes between retries
    retry_jitter=True,         # Add randomness to prevent thundering herd
)
def process_webhook_async(self, webhook_payload: dict) -> dict:
    """Process a webhook event asynchronously with automatic retry.

    This task uses Celery's built-in exponential backoff retry mechanism:
    - Retry 1: ~10s delay
    - Retry 2: ~20s delay
    - Retry 3: ~40s delay
    - Retry 4: ~80s delay
    - Retry 5: ~160s delay (capped at 300s)

    If all retries fail, the task moves to the dead-letter queue.

    Args:
        webhook_payload: The webhook event data as a dict.

    Returns:
        Processing result dict.
    """
    from app.database import SessionLocal
    from app.models.payment import PaymentStatus, WebhookEvent, Payment
    from app.models.booking import Booking, BookingStatus
    from datetime import datetime, timezone

    event_id = webhook_payload.get("event_id", "unknown")

    logger.info(
        "webhook_task_started",
        event_id=event_id,
        attempt=self.request.retries + 1,
        max_retries=self.max_retries,
    )

    db = SessionLocal()
    try:
        # ── Idempotency check ────────────────────────────────────────
        existing_event = (
            db.query(WebhookEvent)
            .filter(WebhookEvent.event_id == event_id)
            .first()
        )
        if existing_event and existing_event.processed:
            logger.info("webhook_task_duplicate", event_id=event_id)
            return {
                "status": "duplicate",
                "message": "Event already processed",
                "event_id": event_id,
            }

        # ── Record event if not exists ───────────────────────────────
        if not existing_event:
            webhook_event = WebhookEvent(
                event_id=event_id,
                event_type=webhook_payload.get("event_type", "unknown"),
                payload=webhook_payload,
                processed=False,
            )
            db.add(webhook_event)
            db.flush()
        else:
            webhook_event = existing_event

        # ── Find and update payment ──────────────────────────────────
        transaction_id = webhook_payload.get("transaction_id")
        payment = (
            db.query(Payment)
            .filter(Payment.transaction_id == transaction_id)
            .first()
        )

        if not payment:
            webhook_event.processed = True
            db.commit()
            logger.warning(
                "webhook_task_unknown_txn",
                event_id=event_id,
                transaction_id=transaction_id,
            )
            return {
                "status": "ignored",
                "message": "Transaction not found",
                "event_id": event_id,
            }

        # ── Update payment and booking ───────────────────────────────
        new_status = webhook_payload.get("status")
        payment.status = PaymentStatus(new_status)
        payment.updated_at = datetime.now(timezone.utc)

        booking = payment.booking
        if new_status == "SUCCESS":
            booking.status = BookingStatus.CONFIRMED
        elif new_status == "FAILED":
            booking.status = BookingStatus.FAILED

        booking.updated_at = datetime.now(timezone.utc)
        webhook_event.processed = True

        db.commit()

        logger.info(
            "webhook_task_processed",
            event_id=event_id,
            transaction_id=transaction_id,
            payment_status=new_status,
            attempt=self.request.retries + 1,
        )
        return {
            "status": "processed",
            "message": "Payment status updated successfully",
            "event_id": event_id,
        }

    except Exception as exc:
        db.rollback()
        logger.error(
            "webhook_task_failed",
            event_id=event_id,
            attempt=self.request.retries + 1,
            error=str(exc),
        )
        # Celery auto-retry will handle this via autoretry_for
        raise

    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="app.tasks.webhook_tasks.retry_failed_webhooks",
    max_retries=0,  # This is a scheduled cleanup task, no retries needed
)
def retry_failed_webhooks(self) -> dict:
    """Scan for unprocessed webhook events and re-queue them.

    This can be run periodically (e.g., via Celery Beat) to pick up
    any webhook events that failed processing.

    Returns:
        Summary of retried events.
    """
    from app.database import SessionLocal
    from app.models.payment import WebhookEvent

    db = SessionLocal()
    try:
        unprocessed = (
            db.query(WebhookEvent)
            .filter(WebhookEvent.processed.is_(False))
            .all()
        )

        retried = 0
        for event in unprocessed:
            if event.payload:
                process_webhook_async.delay(event.payload)
                retried += 1
                logger.info("webhook_retry_queued", event_id=event.event_id)

        logger.info("webhook_retry_scan_complete", retried=retried)
        return {"retried": retried, "total_unprocessed": len(unprocessed)}

    finally:
        db.close()
