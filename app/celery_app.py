"""Celery application configuration.

Uses Redis as both the message broker and result backend.
Tasks are auto-discovered from the `app.tasks` package.
"""

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "eve_healthcare",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task execution
    task_track_started=True,
    task_acks_late=True,          # Acknowledge task after completion (not before)
    worker_prefetch_multiplier=1,  # One task at a time per worker for reliability

    # Retry defaults
    task_default_retry_delay=30,   # 30 seconds default retry delay
    task_max_retries=5,            # Max 5 retries per task

    # Result expiration
    result_expires=3600,           # Results expire after 1 hour

    # Task routes (optional, for future scaling)
    task_routes={
        "app.tasks.webhook_tasks.*": {"queue": "webhooks"},
        "app.tasks.cache_tasks.*": {"queue": "cache"},
    },

    # Dead letter queue for failed tasks
    task_reject_on_worker_lost=True,
)

# Auto-discover tasks from the `app.tasks` package
celery_app.autodiscover_tasks(["app.tasks"])
