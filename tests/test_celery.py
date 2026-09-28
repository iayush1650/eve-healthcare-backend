"""Tests for Celery tasks and async webhook processing."""

import pytest


class TestAsyncWebhook:
    """Test async webhook processing via API endpoint."""

    def test_webhook_sync_still_works(self, client, test_payment):
        """Test that sync webhook processing (default) still works."""
        response = client.post(
            "/api/v1/payments/webhook/",
            json={
                "event_id": "EVT-SYNC-001",
                "event_type": "payment.completed",
                "transaction_id": test_payment.transaction_id,
                "status": "SUCCESS",
                "amount": "500.00",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"

    def test_webhook_async_without_celery(self, client, test_payment):
        """Test async webhook endpoint gracefully handles missing Celery."""
        response = client.post(
            "/api/v1/payments/webhook/?async_processing=true",
            json={
                "event_id": "EVT-ASYNC-001",
                "event_type": "payment.completed",
                "transaction_id": test_payment.transaction_id,
                "status": "SUCCESS",
                "amount": "500.00",
            },
        )
        assert response.status_code == 200
        data = response.json()
        # When Celery/Redis is not running, it should return error or queued
        assert data["status"] in ["queued", "error"]
        assert data["event_id"] == "EVT-ASYNC-001"

    def test_webhook_sync_idempotency_preserved(self, client, test_payment):
        """Test that sync idempotency is preserved after adding async support."""
        webhook_data = {
            "event_id": "EVT-IDEM-SYNC-001",
            "event_type": "payment.completed",
            "transaction_id": test_payment.transaction_id,
            "status": "SUCCESS",
            "amount": "500.00",
        }

        # First call
        resp1 = client.post("/api/v1/payments/webhook/", json=webhook_data)
        assert resp1.status_code == 200
        assert resp1.json()["status"] == "processed"

        # Duplicate call
        resp2 = client.post("/api/v1/payments/webhook/", json=webhook_data)
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "duplicate"


class TestWebhookTaskModule:
    """Test the webhook task module can be imported and configured."""

    def test_celery_app_configuration(self):
        """Test that the Celery app is configured correctly."""
        from app.celery_app import celery_app

        assert celery_app.main == "eve_healthcare"
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.task_acks_late is True
        assert celery_app.conf.enable_utc is True

    def test_webhook_task_is_registered(self):
        """Test that the webhook processing task exists."""
        from app.tasks.webhook_tasks import process_webhook_async

        assert process_webhook_async.name == "app.tasks.webhook_tasks.process_webhook_async"
        assert process_webhook_async.max_retries == 5

    def test_retry_task_is_registered(self):
        """Test that the retry scan task exists."""
        from app.tasks.webhook_tasks import retry_failed_webhooks

        assert retry_failed_webhooks.name == "app.tasks.webhook_tasks.retry_failed_webhooks"
