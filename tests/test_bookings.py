"""Tests for booking endpoints."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest


class TestCreateBooking:
    """Test suite for POST /api/v1/bookings/."""

    def test_create_booking_success(self, client, auth_headers, test_centre_test):
        """Test successful booking creation."""
        future_dt = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        response = client.post(
            "/api/v1/bookings/",
            headers=auth_headers,
            json={
                "centre_test_id": str(test_centre_test.id),
                "appointment_datetime": future_dt,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "PENDING"
        assert float(data["amount"]) == 500.00
        assert data["centre_name"] == "Test Diagnostics"
        assert data["test_name"] == "Complete Blood Count"

    def test_create_booking_unauthenticated(self, client, test_centre_test):
        """Test booking without authentication."""
        future_dt = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        response = client.post(
            "/api/v1/bookings/",
            json={
                "centre_test_id": str(test_centre_test.id),
                "appointment_datetime": future_dt,
            },
        )
        assert response.status_code in [401, 403]  # No Bearer token

    def test_create_booking_invalid_centre_test(self, client, auth_headers):
        """Test booking with non-existent centre-test ID."""
        future_dt = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        response = client.post(
            "/api/v1/bookings/",
            headers=auth_headers,
            json={
                "centre_test_id": str(uuid.uuid4()),
                "appointment_datetime": future_dt,
            },
        )
        assert response.status_code == 404

    def test_create_booking_past_datetime(self, client, auth_headers, test_centre_test):
        """Test booking with past appointment time."""
        past_dt = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        response = client.post(
            "/api/v1/bookings/",
            headers=auth_headers,
            json={
                "centre_test_id": str(test_centre_test.id),
                "appointment_datetime": past_dt,
            },
        )
        assert response.status_code == 422


class TestListBookings:
    """Test suite for GET /api/v1/bookings/."""

    def test_list_bookings(self, client, auth_headers, test_booking):
        """Test listing user bookings."""
        response = client.get("/api/v1/bookings/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["bookings"]) >= 1

    def test_list_bookings_unauthenticated(self, client):
        """Test listing bookings without auth."""
        response = client.get("/api/v1/bookings/")
        assert response.status_code in [401, 403]


class TestGetBooking:
    """Test suite for GET /api/v1/bookings/{id}."""

    def test_get_booking(self, client, auth_headers, test_booking):
        """Test retrieving a specific booking."""
        response = client.get(
            f"/api/v1/bookings/{test_booking.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_booking.id)
        assert data["status"] == "PENDING"

    def test_get_nonexistent_booking(self, client, auth_headers):
        """Test retrieving a booking that doesn't exist."""
        response = client.get(
            f"/api/v1/bookings/{uuid.uuid4()}", headers=auth_headers
        )
        assert response.status_code == 404

    def test_get_other_users_booking(self, client, test_booking, db_session):
        """Test that a user cannot view another user's booking."""
        from app.core.security import create_access_token, hash_password
        from app.models.user import User

        other_user = User(
            email="other@example.com",
            full_name="Other User",
            password_hash=hash_password("otherpassword"),
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        other_token = create_access_token(data={"sub": str(other_user.id)})
        other_headers = {"Authorization": f"Bearer {other_token}"}

        response = client.get(
            f"/api/v1/bookings/{test_booking.id}", headers=other_headers
        )
        assert response.status_code == 403


class TestCancelBooking:
    """Test suite for POST /api/v1/bookings/{id}/cancel."""

    def test_cancel_pending_booking(self, client, auth_headers, test_booking):
        """Test cancelling a PENDING booking."""
        response = client.post(
            f"/api/v1/bookings/{test_booking.id}/cancel",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "CANCELLED"

    def test_cancel_nonexistent_booking(self, client, auth_headers):
        """Test cancelling a booking that doesn't exist."""
        response = client.post(
            f"/api/v1/bookings/{uuid.uuid4()}/cancel",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 404

    def test_cannot_cancel_already_cancelled(
        self, client, auth_headers, test_booking, db_session
    ):
        """Test that a cancelled booking cannot be cancelled again."""
        from app.models.booking import BookingStatus

        test_booking.status = BookingStatus.CANCELLED
        db_session.commit()

        response = client.post(
            f"/api/v1/bookings/{test_booking.id}/cancel",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 400
