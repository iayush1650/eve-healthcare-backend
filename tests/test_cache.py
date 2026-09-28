"""Tests for Redis caching functionality."""

import pytest
from unittest.mock import patch, MagicMock


class TestCacheIntegration:
    """Test caching behavior in centre/test endpoints."""

    def test_list_centres_caches_result(self, client, test_centre):
        """Test that listing centres returns data and caching is attempted."""
        # First call — should query DB
        response1 = client.get("/api/v1/centres/")
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["total"] >= 1

        # Second call — should still work (cache hit or miss)
        response2 = client.get("/api/v1/centres/")
        assert response2.status_code == 200
        data2 = response2.json()

        # Data should be identical
        assert data1["total"] == data2["total"]

    def test_get_centre_caches_result(self, client, test_centre):
        """Test that getting a centre detail returns data consistently."""
        response1 = client.get(f"/api/v1/centres/{test_centre.id}")
        assert response1.status_code == 200

        response2 = client.get(f"/api/v1/centres/{test_centre.id}")
        assert response2.status_code == 200
        assert response1.json()["name"] == response2.json()["name"]

    def test_list_tests_caches_result(self, client, test_diagnostic_test):
        """Test that listing tests returns data consistently."""
        response1 = client.get("/api/v1/centres/tests/all")
        assert response1.status_code == 200

        response2 = client.get("/api/v1/centres/tests/all")
        assert response2.status_code == 200
        assert response1.json()["total"] == response2.json()["total"]

    def test_create_centre_invalidates_cache(self, client, test_centre):
        """Test that creating a new centre doesn't break subsequent listings."""
        # List first
        response1 = client.get("/api/v1/centres/")
        count1 = response1.json()["total"]

        # Create new centre
        client.post(
            "/api/v1/centres/",
            json={
                "name": "Cache Test Centre",
                "location": "Cache City",
            },
        )

        # List again — should show updated count
        response2 = client.get("/api/v1/centres/")
        count2 = response2.json()["total"]
        assert count2 == count1 + 1

    def test_create_test_invalidates_cache(self, client, test_diagnostic_test):
        """Test that creating a new test doesn't break subsequent listings."""
        response1 = client.get("/api/v1/centres/tests/all")
        count1 = response1.json()["total"]

        client.post(
            "/api/v1/centres/tests",
            json={
                "name": "Cache Test",
                "description": "Testing cache invalidation",
                "category": "CacheCategory",
            },
        )

        response2 = client.get("/api/v1/centres/tests/all")
        count2 = response2.json()["total"]
        assert count2 == count1 + 1


class TestCacheHealthEndpoint:
    """Test cache health check endpoint."""

    def test_cache_health_endpoint_exists(self, client):
        """Test that the /health/cache endpoint responds."""
        response = client.get("/health/cache")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "backend" in data
        assert data["backend"] == "redis"


class TestCacheModule:
    """Test the cache utility module directly."""

    def test_cache_key_builders(self):
        """Test cache key builder functions produce valid keys."""
        from app.core.cache import (
            build_centres_list_key,
            build_centre_detail_key,
            build_tests_list_key,
        )

        key1 = build_centres_list_key(1, 20, None)
        assert "centres:list" in key1
        assert "all" in key1

        key2 = build_centres_list_key(1, 20, "Mumbai")
        assert "mumbai" in key2

        key3 = build_centre_detail_key("some-uuid-123")
        assert "centres:detail" in key3
        assert "some-uuid-123" in key3

        key4 = build_tests_list_key(2, 10, "Hematology")
        assert "tests:list" in key4
        assert "hematology" in key4

    def test_cache_graceful_degradation(self):
        """Test that cache operations don't fail when Redis is unavailable."""
        from app.core.cache import cache_get, cache_set, cache_delete

        # These should return gracefully when Redis is not running
        # (they return None/False instead of raising)
        result_get = cache_get("nonexistent:key")
        assert result_get is None

        # cache_set returns False if Redis unavailable
        result_set = cache_set("test:key", {"data": "test"})
        assert isinstance(result_set, bool)

        result_delete = cache_delete("test:key")
        assert isinstance(result_delete, bool)
