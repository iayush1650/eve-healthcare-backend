"""Redis caching utility with graceful fallback.

Provides a thin wrapper around redis-py with:
- Connection pooling (via REDIS_URL)
- JSON serialization for cached values
- TTL-based expiration
- Pattern-based cache invalidation
- Graceful degradation when Redis is unavailable
"""

import json
from typing import Any

import structlog
import redis

from app.config import get_settings

logger = structlog.get_logger(__name__)

settings = get_settings()

# ── Redis Connection Pool ────────────────────────────────────────────────────

_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis | None:
    """Get or create a Redis client with connection pooling.

    Returns None if Redis is not available (graceful degradation).
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    try:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            retry_on_timeout=True,
        )
        # Test connection
        _redis_client.ping()
        logger.info("redis_connected", url=settings.REDIS_URL)
        return _redis_client
    except (redis.ConnectionError, redis.TimeoutError) as e:
        logger.warning("redis_unavailable", error=str(e))
        _redis_client = None
        return None


# ── Cache Operations ─────────────────────────────────────────────────────────

# Default TTL values (in seconds)
CACHE_TTL_SHORT = 60          # 1 minute — for frequently changing data
CACHE_TTL_MEDIUM = 300        # 5 minutes — for centre/test listings
CACHE_TTL_LONG = 900          # 15 minutes — for individual centre details

# Cache key prefixes
KEY_PREFIX = "eve:"
CENTRES_LIST_KEY = f"{KEY_PREFIX}centres:list"
CENTRE_DETAIL_KEY = f"{KEY_PREFIX}centres:detail"
TESTS_LIST_KEY = f"{KEY_PREFIX}tests:list"


def cache_get(key: str) -> Any | None:
    """Retrieve a cached value by key.

    Returns:
        Deserialized Python object, or None if not found or Redis unavailable.
    """
    client = get_redis_client()
    if not client:
        return None

    try:
        data = client.get(key)
        if data is not None:
            logger.debug("cache_hit", key=key)
            return json.loads(data)
        logger.debug("cache_miss", key=key)
        return None
    except (redis.RedisError, json.JSONDecodeError) as e:
        logger.warning("cache_get_error", key=key, error=str(e))
        return None


def cache_set(key: str, value: Any, ttl: int = CACHE_TTL_MEDIUM) -> bool:
    """Store a value in cache with a TTL.

    Args:
        key: Cache key.
        value: Python object (must be JSON-serializable).
        ttl: Time-to-live in seconds.

    Returns:
        True if cached successfully, False otherwise.
    """
    client = get_redis_client()
    if not client:
        return False

    try:
        serialized = json.dumps(value, default=str)
        client.setex(key, ttl, serialized)
        logger.debug("cache_set", key=key, ttl=ttl)
        return True
    except (redis.RedisError, TypeError) as e:
        logger.warning("cache_set_error", key=key, error=str(e))
        return False


def cache_delete(key: str) -> bool:
    """Delete a specific cache key.

    Returns:
        True if deleted, False otherwise.
    """
    client = get_redis_client()
    if not client:
        return False

    try:
        client.delete(key)
        logger.debug("cache_deleted", key=key)
        return True
    except redis.RedisError as e:
        logger.warning("cache_delete_error", key=key, error=str(e))
        return False


def cache_invalidate_pattern(pattern: str) -> int:
    """Delete all cache keys matching a pattern.

    Uses SCAN to avoid blocking Redis with KEYS command.

    Args:
        pattern: Glob-style pattern (e.g., "eve:centres:*").

    Returns:
        Number of keys deleted.
    """
    client = get_redis_client()
    if not client:
        return 0

    try:
        deleted = 0
        for key in client.scan_iter(match=pattern, count=100):
            client.delete(key)
            deleted += 1
        if deleted > 0:
            logger.info("cache_invalidated", pattern=pattern, count=deleted)
        return deleted
    except redis.RedisError as e:
        logger.warning("cache_invalidate_error", pattern=pattern, error=str(e))
        return 0


# ── Cache Key Builders ───────────────────────────────────────────────────────


def build_centres_list_key(page: int, page_size: int, location: str | None) -> str:
    """Build a cache key for centre list queries."""
    location_part = location.lower().strip() if location else "all"
    return f"{CENTRES_LIST_KEY}:{location_part}:p{page}:s{page_size}"


def build_centre_detail_key(centre_id: str) -> str:
    """Build a cache key for a single centre."""
    return f"{CENTRE_DETAIL_KEY}:{centre_id}"


def build_tests_list_key(page: int, page_size: int, category: str | None) -> str:
    """Build a cache key for test list queries."""
    category_part = category.lower().strip() if category else "all"
    return f"{TESTS_LIST_KEY}:{category_part}:p{page}:s{page_size}"


def invalidate_centres_cache() -> None:
    """Invalidate all centre-related cache entries."""
    cache_invalidate_pattern(f"{KEY_PREFIX}centres:*")


def invalidate_tests_cache() -> None:
    """Invalidate all test-related cache entries."""
    cache_invalidate_pattern(f"{KEY_PREFIX}tests:*")
    # Also invalidate centres since they include test info
    cache_invalidate_pattern(f"{KEY_PREFIX}centres:*")
