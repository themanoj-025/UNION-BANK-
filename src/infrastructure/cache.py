"""
infrastructure/cache.py  –  Cache abstraction for Union Bank.

Provides a clean cache abstraction with two implementations:
- RedisCache: production-grade, backed by Redis
- NullCache: no-op fallback for development/testing

Usage:
    from infrastructure.cache import cache

    @cache.cached(ttl=60)
    def expensive_query():
        ...
"""

from __future__ import annotations

import functools
import hashlib
import json
import logging
from datetime import timedelta
from typing import Any, Callable, Optional

logger = logging.getLogger("union_bank.cache")


# ═══════════════════════════════════════════════════════════════════════════════
#  Cache Protocol
# ═══════════════════════════════════════════════════════════════════════════════


class Cache:
    """Abstract cache interface.

    All operations are safe to call even if the backing store is unavailable
    — failures are logged and treated as cache misses.
    """

    def get(self, key: str) -> Optional[str]:
        """Get a value from cache. Returns None on miss or error."""
        raise NotImplementedError

    def get_json(self, key: str) -> Optional[Any]:
        """Get a JSON-deserialized value from cache."""
        raw = self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    def set(self, key: str, value: str, ttl: int = 60) -> None:
        """Set a value in cache with TTL in seconds."""
        raise NotImplementedError

    def set_json(self, key: str, value: Any, ttl: int = 60) -> None:
        """Set a JSON-serializable value in cache."""
        self.set(key, json.dumps(value, default=str), ttl=ttl)

    def delete(self, key: str) -> None:
        """Delete a key from cache."""
        raise NotImplementedError

    def clear_pattern(self, pattern: str) -> None:
        """Delete all keys matching a glob pattern (e.g. 'accounts:*')."""
        raise NotImplementedError

    def cached(self, ttl: int = 60, key_prefix: str = ""):
        """Decorator: cache the return value of a function.

        The cache key is derived from the function name + args.
        Only works for functions with JSON-serializable arguments.

        Usage:
            @cache.cached(ttl=120, key_prefix="stats")
            def get_bank_statistics():
                ...
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Build cache key from function module + name + args
                parts = [func.__module__, func.__qualname__]
                if key_prefix:
                    parts.insert(0, key_prefix)
                if args:
                    parts.append(repr(args))
                if kwargs:
                    parts.append(repr(sorted(kwargs.items())))
                cache_key = hashlib.sha256(
                    ":".join(parts).encode()
                ).hexdigest()

                # Try cache
                cached_value = self.get_json(cache_key)
                if cached_value is not None:
                    return cached_value

                # Compute and cache
                result = func(*args, **kwargs)
                try:
                    self.set_json(cache_key, result, ttl=ttl)
                except Exception:
                    logger.warning("Cache set failed for key %s", cache_key, exc_info=True)
                return result
            return wrapper
        return decorator

    def invalidate(self, key_prefix: str) -> None:
        """Invalidate all cache entries with a given prefix."""
        self.clear_pattern(f"{key_prefix}:*")


# ═══════════════════════════════════════════════════════════════════════════════
#  Null Cache — no-op fallback
# ═══════════════════════════════════════════════════════════════════════════════


class NullCache(Cache):
    """No-op cache — every operation is a miss/no-op.

    Used when Redis is not configured or unavailable.
    """

    def get(self, key: str) -> Optional[str]:
        return None

    def set(self, key: str, value: str, ttl: int = 60) -> None:
        pass

    def delete(self, key: str) -> None:
        pass

    def clear_pattern(self, pattern: str) -> None:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
#  Redis Cache
# ═══════════════════════════════════════════════════════════════════════════════


class RedisCache(Cache):
    """Production cache backed by Redis.

    Falls back to NullCache silently if Redis is unreachable at init time.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        socket_timeout: int = 2,
        **kwargs,
    ):
        self._available = False
        self._redis: Any = None  # redis.Redis instance (lazy import)
        self._host = host
        self._port = port
        self._db = db
        self._password = password
        self._socket_timeout = socket_timeout
        self._kwargs = kwargs

    def _connect(self) -> bool:
        """Lazy Redis connection — try once and cache availability."""
        if self._available:
            return True
        if self._redis is not None:
            return False  # Already tried and failed
        try:
            import redis as redis_module
            self._redis = redis_module.Redis(
                host=self._host,
                port=self._port,
                db=self._db,
                password=self._password,
                socket_timeout=self._socket_timeout,
                decode_responses=True,
                **self._kwargs,
            )
            self._redis.ping()
            self._available = True
            logger.info("Redis cache connected at %s:%s/%s", self._host, self._port, self._db)
        except Exception as exc:
            logger.warning("Redis unavailable — falling back to NullCache: %s", exc)
            self._redis = None
        return self._available

    def get(self, key: str) -> Optional[str]:
        if not self._connect():
            return None
        try:
            return self._redis.get(key)
        except Exception as exc:
            logger.warning("Redis get(%r) failed: %s", key, exc)
            return None

    def set(self, key: str, value: str, ttl: int = 60) -> None:
        if not self._connect():
            return
        try:
            self._redis.setex(key, timedelta(seconds=ttl), value)
        except Exception as exc:
            logger.warning("Redis set(%r) failed: %s", key, exc)

    def delete(self, key: str) -> None:
        if not self._connect():
            return
        try:
            self._redis.delete(key)
        except Exception as exc:
            logger.warning("Redis delete(%r) failed: %s", key, exc)

    def clear_pattern(self, pattern: str) -> None:
        if not self._connect():
            return
        try:
            cursor = 0
            while True:
                cursor, keys = self._redis.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    self._redis.delete(*keys)
                if cursor == 0:
                    break
        except Exception as exc:
            logger.warning("Redis clear_pattern(%r) failed: %s", pattern, exc)


# ═══════════════════════════════════════════════════════════════════════════════
#  Global singleton (lazy initialised from settings)
# ═══════════════════════════════════════════════════════════════════════════════

_cache_instance: Optional[Cache] = None


def get_cache() -> Cache:
    """Get the global cache singleton.

    Returns a RedisCache if Redis is configured and reachable,
    otherwise returns a NullCache.

    The cache can be overridden via set_cache() for testing.
    """
    global _cache_instance
    if _cache_instance is None:
        from config import settings

        redis_url = getattr(settings, "REDIS_URL", None)
        if redis_url:
            # Parse redis:// URL
            try:
                from urllib.parse import urlparse
                parsed = urlparse(redis_url)
                _cache_instance = RedisCache(
                    host=parsed.hostname or "localhost",
                    port=parsed.port or 6379,
                    db=int(parsed.path.lstrip("/") or 0),
                    password=parsed.password,
                )
            except Exception:
                logger.warning("Failed to parse REDIS_URL, falling back to NullCache", exc_info=True)
                _cache_instance = NullCache()
        else:
            _cache_instance = NullCache()
    return _cache_instance


def set_cache(cache: Cache) -> None:
    """Override the global cache (useful for testing with FakeCache or NullCache)."""
    global _cache_instance
    _cache_instance = cache


def reset_cache() -> None:
    """Reset the global cache singleton."""
    global _cache_instance
    _cache_instance = None


# Pre-export the cached decorator from the active cache
def cached(ttl: int = 60, key_prefix: str = ""):
    """Convenience decorator wrapping the global cache's cached method."""
    return get_cache().cached(ttl=ttl, key_prefix=key_prefix)
