"""Tests for payment and webhook endpoints."""

import uuid

import pytest


class TestProcessPayment:
    """Test suite for POST /api/v1/payments/."""

    def test_process_payment_success(self, client, auth_headers, test_booking):
        """Test simulated payment processing."""
        response = client.post(
            "/api/v1/payments/",
            headers=auth_headers,
            json={"booking_id": str(test_booking.id)},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["booking_id"] == str(test_booking.id)
        assert data["status"] in ["SUCCESS", "FAILED"]
        assert data["transaction_id"].startswith("TXN-")
        assert float(data["amount"]) == 500.00

    def test_process_payment_unauthenticated(self, client, test_booking):
        """Test payment without authentication."""
        response = client.post(
            "/api/v1/payments/",
            json={"booking_id": str(test_booking.id)},
        )
        assert response.status_code in [401, 403]

    def test_process_payment_nonexistent_booking(self, client, auth_headers):
        """Test payment for non-existent booking."""
        response = client.post(
            "/api/v1/payments/",
            headers=auth_headers,
            json={"booking_id": str(uuid.uuid4())},
        )
        assert response.status_code == 404

    def test_process_payment_duplicate(self, client, auth_headers, test_booking):
        """Test that a booking cannot be paid for twice."""
        # First payment
        client.post(
            "/api/v1/payments/",
            headers=auth_headers,
            json={"booking_id": str(test_booking.id)},
        )
        # Second payment attempt
        response = client.post(
            "/api/v1/payments/",
            headers=auth_headers,
            json={"booking_id": str(test_booking.id)},
        )
        # Should fail — either 409 (duplicate) or 400 (not PENDING)
        assert response.status_code in [400, 409]

    def test_process_payment_other_users_booking(
        self, client, test_booking, db_session
    ):
        """Test that a user cannot pay for another user's booking."""
        from app.core.security import create_access_token, hash_password
        from app.models.user import User

        other_user = User(
            email="other2@example.com",
            full_name="Other User 2",
            password_hash=hash_password("otherpassword"),
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        other_token = create_access_token(data={"sub": str(other_user.id)})
        headers = {"Authorization": f"Bearer {other_token}"}

        response = client.post(
            "/api/v1/payments/",
            headers=headers,
            json={"booking_id": str(test_booking.id)},
        )
        assert response.status_code == 400


class TestPaymentWebhook:
    """Test suite for POST /api/v1/payments/webhook/."""

    def test_webhook_success(self, client, test_payment):
        """Test successful webhook processing."""
        response = client.post(
            "/api/v1/payments/webhook/",
            json={
                "event_id": "EVT-001",
                "event_type": "payment.completed",
                "transaction_id": test_payment.transaction_id,
                "status": "SUCCESS",
                "amount": "500.00",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"
        assert data["event_id"] == "EVT-001"

    def test_webhook_idempotency(self, client, test_payment):
        """Test that duplicate webhook events are safely ignored."""
        webhook_data = {
            "event_id": "EVT-IDEMPOTENT-001",
            "event_type": "payment.completed",
            "transaction_id": test_payment.transaction_id,
            "status": "SUCCESS",
            "amount": "500.00",
        }

        # First call — should process
        response1 = client.post("/api/v1/payments/webhook/", json=webhook_data)
        assert response1.status_code == 200
        assert response1.json()["status"] == "processed"

        # Second call with same event_id — should be ignored
        response2 = client.post("/api/v1/payments/webhook/", json=webhook_data)
        assert response2.status_code == 200
        assert response2.json()["status"] == "duplicate"

        # Third call — still duplicate
        response3 = client.post("/api/v1/payments/webhook/", json=webhook_data)
        assert response3.status_code == 200
        assert response3.json()["status"] == "duplicate"

    def test_webhook_unknown_transaction(self, client):
        """Test webhook with unknown transaction ID."""
        response = client.post(
            "/api/v1/payments/webhook/",
            json={
                "event_id": "EVT-UNKNOWN-001",
                "event_type": "payment.completed",
                "transaction_id": "TXN-DOESNOTEXIST",
                "status": "SUCCESS",
                "amount": "100.00",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"

    def test_webhook_failed_payment(self, client, test_payment):
        """Test webhook with FAILED payment status."""
        response = client.post(
            "/api/v1/payments/webhook/",
            json={
                "event_id": "EVT-FAIL-001",
                "event_type": "payment.failed",
                "transaction_id": test_payment.transaction_id,
                "status": "FAILED",
                "amount": "500.00",
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "processed"

    def test_webhook_missing_fields(self, client):
        """Test webhook with missing required fields."""
        response = client.post(
            "/api/v1/payments/webhook/",
            json={"event_id": "EVT-INCOMPLETE"},
        )
        assert response.status_code == 422

    def test_webhook_multiple_different_events(self, client, test_payment):
        """Test processing multiple different webhook events."""
        # First event
        resp1 = client.post(
            "/api/v1/payments/webhook/",
            json={
                "event_id": "EVT-MULTI-001",
                "event_type": "payment.pending",
                "transaction_id": test_payment.transaction_id,
                "status": "PENDING",
                "amount": "500.00",
            },
        )
        assert resp1.status_code == 200

        # Second different event
        resp2 = client.post(
            "/api/v1/payments/webhook/",
            json={
                "event_id": "EVT-MULTI-002",
                "event_type": "payment.completed",
                "transaction_id": test_payment.transaction_id,
                "status": "SUCCESS",
                "amount": "500.00",
            },
        )
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "processed"
