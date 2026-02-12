"""
Redis-based caching system for optimization results and API responses.
Uses redis.asyncio to avoid blocking the event loop.

Falls back gracefully when Redis is unavailable.
"""

import hashlib
import inspect
import json
import logging
from collections.abc import Callable
from functools import wraps
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import redis (graceful degradation)
try:
    import redis as sync_redis
    import redis.asyncio as aioredis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis not available. Install with: pip install redis")


class RedisCache:
    """
    Async Redis-based caching for optimization results and API responses.

    Uses redis.asyncio to avoid blocking the FastAPI event loop.
    Falls back gracefully when Redis is unavailable.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: str | None = None,
        decode_responses: bool = True,
    ):
        self.available = False
        self._host = host
        self._port = port
        self._db = db
        self._password = password
        self._decode_responses = decode_responses
        self.client = None

        if not REDIS_AVAILABLE:
            logger.warning("Redis library not installed. Cache disabled.")
            return

        # Probe connectivity synchronously at startup
        try:
            probe = sync_redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                socket_timeout=2,
                socket_connect_timeout=2,
            )
            probe.ping()
            probe.close()
            self.available = True
            logger.info(f"Redis cache available: {host}:{port}")
        except Exception as e:
            self.available = False
            logger.warning(f"Redis not available: {e}. Falling back to no-op cache.")

    async def _get_client(self):
        """Lazy-initialize the async Redis client."""
        if not self.available or not REDIS_AVAILABLE:
            return None
        if self.client is None:
            self.client = aioredis.Redis(
                host=self._host,
                port=self._port,
                db=self._db,
                password=self._password,
                decode_responses=self._decode_responses,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
        return self.client

    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate consistent cache key from function arguments."""
        data = {
            "args": str(args),
            "kwargs": {k: str(v) for k, v in sorted(kwargs.items())},
        }
        serialized = json.dumps(data, sort_keys=True)
        hash_value = hashlib.sha256(serialized.encode()).hexdigest()[:16]
        return f"{prefix}:{hash_value}"

    async def get(self, key: str) -> dict | None:
        """Retrieve value from cache (async)."""
        client = await self._get_client()
        if client is None:
            return None

        try:
            value = await client.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            logger.debug(f"Cache MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"Cache get error for {key}: {e}")
            return None

    async def set(self, key: str, value: dict, ttl_seconds: int = 3600) -> bool:
        """Store value in cache (async)."""
        client = await self._get_client()
        if client is None:
            return False

        try:
            serialized = json.dumps(value)
            await client.setex(key, ttl_seconds, serialized)
            logger.debug(f"Cache SET: {key} (TTL: {ttl_seconds}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete specific cache key (async)."""
        client = await self._get_client()
        if client is None:
            return False

        try:
            deleted = await client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return bool(deleted)
        except Exception as e:
            logger.error(f"Cache delete error for {key}: {e}")
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching a pattern (async)."""
        client = await self._get_client()
        if client is None:
            return 0

        try:
            keys = []
            async for key in client.scan_iter(match=pattern, count=100):
                keys.append(key)
            if keys:
                deleted = await client.delete(*keys)
                logger.info(f"Cache INVALIDATE: {pattern} ({deleted} keys)")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Cache invalidate error for {pattern}: {e}")
            return 0

    async def get_stats(self) -> dict:
        """Get cache statistics (async)."""
        client = await self._get_client()
        if client is None:
            return {"available": False}

        try:
            info = await client.info("stats")
            db_size = await client.dbsize()
            return {
                "available": True,
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "keys": db_size,
                "hit_rate": info.get("keyspace_hits", 0)
                / max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0)),
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"available": False, "error": str(e)}

    async def close(self):
        """Close the Redis connection."""
        if self.client:
            await self.client.close()
            self.client = None


# Singleton instance for global use
redis_cache = RedisCache()


def cached(prefix: str, ttl: int = 3600, cache_instance: Optional["RedisCache"] = None):
    """Decorator to cache async function results in Redis."""

    def decorator(func: Callable):
        _cache = cache_instance

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            nonlocal _cache
            if _cache is None:
                _cache = redis_cache

            cache_key = _cache._generate_key(prefix, *args[1:], **kwargs)

            cached_result = await _cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            result = await func(*args, **kwargs)

            if result is not None:
                await _cache.set(cache_key, result, ttl)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
