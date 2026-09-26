"""Tests for authentication endpoints."""

import pytest


class TestSignup:
    """Test suite for POST /api/v1/auth/signup."""

    def test_signup_success(self, client):
        """Test successful user registration."""
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "new@example.com",
                "full_name": "New User",
                "password": "securepassword123",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "new@example.com"
        assert data["user"]["full_name"] == "New User"
        assert data["user"]["is_active"] is True

    def test_signup_duplicate_email(self, client, test_user):
        """Test signup with already registered email."""
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "test@example.com",  # Same as test_user
                "full_name": "Another User",
                "password": "securepassword123",
            },
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_signup_invalid_email(self, client):
        """Test signup with invalid email format."""
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "not-an-email",
                "full_name": "Bad Email",
                "password": "securepassword123",
            },
        )
        assert response.status_code == 422

    def test_signup_short_password(self, client):
        """Test signup with password shorter than 8 characters."""
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "short@example.com",
                "full_name": "Short Pass",
                "password": "abc",
            },
        )
        assert response.status_code == 422

    def test_signup_missing_fields(self, client):
        """Test signup with missing required fields."""
        response = client.post(
            "/api/v1/auth/signup",
            json={"email": "missing@example.com"},
        )
        assert response.status_code == 422


class TestLogin:
    """Test suite for POST /api/v1/auth/login."""

    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "test@example.com"

    def test_login_wrong_password(self, client, test_user):
        """Test login with incorrect password."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent email."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nobody@example.com",
                "password": "somepassword123",
            },
        )
        assert response.status_code == 401

    def test_login_missing_fields(self, client):
        """Test login with missing fields."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com"},
        )
        assert response.status_code == 422
