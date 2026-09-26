"""Tests for diagnostic centres and tests endpoints."""

import pytest


class TestCentres:
    """Test suite for diagnostic centre endpoints."""

    def test_create_centre(self, client):
        """Test creating a new diagnostic centre."""
        response = client.post(
            "/api/v1/centres/",
            json={
                "name": "New Centre",
                "location": "Mumbai",
                "address": "123 Main St",
                "phone": "+91-1234567890",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Centre"
        assert data["location"] == "Mumbai"
        assert data["is_active"] is True

    def test_list_centres(self, client, test_centre):
        """Test listing diagnostic centres."""
        response = client.get("/api/v1/centres/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["centres"]) >= 1

    def test_list_centres_with_location_filter(self, client, test_centre):
        """Test filtering centres by location."""
        response = client.get("/api/v1/centres/?location=Test")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

        response = client.get("/api/v1/centres/?location=NonExistent")
        data = response.json()
        assert data["total"] == 0

    def test_get_centre(self, client, test_centre):
        """Test getting a single centre by ID."""
        response = client.get(f"/api/v1/centres/{test_centre.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Diagnostics"

    def test_get_nonexistent_centre(self, client):
        """Test getting a centre that doesn't exist."""
        import uuid

        fake_id = uuid.uuid4()
        response = client.get(f"/api/v1/centres/{fake_id}")
        assert response.status_code == 404

    def test_list_centres_pagination(self, client, test_centre):
        """Test pagination parameters."""
        response = client.get("/api/v1/centres/?page=1&page_size=5")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5


class TestDiagnosticTests:
    """Test suite for diagnostic test endpoints."""

    def test_create_test(self, client):
        """Test creating a new diagnostic test."""
        response = client.post(
            "/api/v1/centres/tests",
            json={
                "name": "Blood Sugar",
                "description": "Measures glucose levels",
                "category": "Biochemistry",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Blood Sugar"
        assert data["category"] == "Biochemistry"

    def test_list_tests(self, client, test_diagnostic_test):
        """Test listing diagnostic tests."""
        response = client.get("/api/v1/centres/tests/all")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    def test_list_tests_category_filter(self, client, test_diagnostic_test):
        """Test filtering tests by category."""
        response = client.get("/api/v1/centres/tests/all?category=Hematology")
        data = response.json()
        assert data["total"] >= 1


class TestCentreTestLinking:
    """Test suite for linking tests to centres."""

    def test_link_test_to_centre(self, client, test_centre, test_diagnostic_test):
        """Test linking a test to a centre with pricing."""
        response = client.post(
            "/api/v1/centres/tests/link",
            json={
                "centre_id": str(test_centre.id),
                "test_id": str(test_diagnostic_test.id),
                "price": "500.00",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["centre_name"] == "Test Diagnostics"
        assert data["test_name"] == "Complete Blood Count"
        assert float(data["price"]) == 500.00

    def test_link_duplicate(self, client, test_centre_test, test_centre, test_diagnostic_test):
        """Test duplicate centre-test link returns conflict."""
        response = client.post(
            "/api/v1/centres/tests/link",
            json={
                "centre_id": str(test_centre.id),
                "test_id": str(test_diagnostic_test.id),
                "price": "600.00",
            },
        )
        assert response.status_code == 409
