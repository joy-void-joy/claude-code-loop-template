"""Simple TTL-based caching for API calls.

Provides a decorator that caches function results in memory with time-based
expiration. Useful for avoiding redundant API calls during a session.
"""

import asyncio
import hashlib
import logging
import time
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import TypedDict, cast

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CacheEntry(BaseModel):
    """A cached value with expiration time."""

    value: object
    expires_at: float


class CacheStats(TypedDict):
    """Statistics for a TTLCache instance."""

    size: int
    hits: int
    misses: int
    hit_rate: float


class TTLCache:
    """Thread-safe TTL cache for storing API responses.

    Args:
        default_ttl: Default time-to-live in seconds for cached values.
        max_size: Maximum number of entries before eviction.

    Example:
        cache = TTLCache(default_ttl=300)  # 5 minute cache

        @cache.cached()
        async def search_api(query: str) -> list:
            return await api.search(query)
    """

    def __init__(self, default_ttl: float = 300.0, max_size: int = 1000) -> None:
        self._cache: dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    def _make_key(
        self, func_name: str, args: tuple[object, ...], kwargs: dict[str, object]
    ) -> str:
        """Generate a cache key from function name and arguments."""
        key_parts = [func_name]

        for arg in args:
            key_parts.append(repr(arg))

        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v!r}")

        key_str = "|".join(key_parts)
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    async def get(self, key: str) -> tuple[bool, object]:
        """Get a value from cache.

        Args:
            key: Cache key

        Returns:
            Tuple of (found, value). If not found or expired, (False, None).
        """
        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._misses += 1
                return False, None

            if time.time() > entry.expires_at:
                del self._cache[key]
                self._misses += 1
                return False, None

            self._hits += 1
            return True, entry.value

    async def set(self, key: str, value: object, ttl: float | None = None) -> None:
        """Store a value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        if ttl is None:
            ttl = self._default_ttl

        async with self._lock:
            if len(self._cache) >= self._max_size:
                self._evict_expired()

            if len(self._cache) >= self._max_size:
                oldest_key = min(
                    self._cache.keys(), key=lambda k: self._cache[k].expires_at
                )
                del self._cache[oldest_key]

            self._cache[key] = CacheEntry(value=value, expires_at=time.time() + ttl)

    def _evict_expired(self) -> int:
        """Remove all expired entries. Call while holding lock.

        Returns:
            Number of entries evicted.
        """
        now = time.time()
        expired_keys = [k for k, v in self._cache.items() if v.expires_at < now]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)

    async def clear(self) -> None:
        """Clear all cached entries."""
        async with self._lock:
            self._cache.clear()

    @property
    def stats(self) -> CacheStats:
        """Return cache statistics."""
        return CacheStats(
            size=len(self._cache),
            hits=self._hits,
            misses=self._misses,
            hit_rate=self._hits / max(1, self._hits + self._misses),
        )

    def cached[**P, T](
        self, ttl: float | None = None
    ) -> Callable[
        [Callable[P, Coroutine[object, object, T]]],
        Callable[P, Coroutine[object, object, T]],
    ]:
        """Decorator for caching async function results.

        Args:
            ttl: Time-to-live in seconds for this function's cache entries.
                 Uses cache default if None.

        Returns:
            Decorator function.

        Example:
            @cache.cached(ttl=600)
            async def fetch_data(query: str) -> dict:
                return await api.fetch(query)
        """

        def decorator(
            func: Callable[P, Coroutine[object, object, T]],
        ) -> Callable[P, Coroutine[object, object, T]]:
            @wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                key = self._make_key(func.__name__, args, kwargs)

                found, value = await self.get(key)
                if found:
                    logger.debug("Cache hit for %s", func.__name__)
                    return cast(T, value)

                logger.debug("Cache miss for %s", func.__name__)
                result = await func(*args, **kwargs)

                await self.set(key, result, ttl)

                return result

            return wrapper

        return decorator


# Global cache instance for API calls (5 minute TTL)
api_cache = TTLCache(default_ttl=300.0, max_size=500)


def cached[**P, T](
    ttl: float | None = None,
) -> Callable[
    [Callable[P, Coroutine[object, object, T]]],
    Callable[P, Coroutine[object, object, T]],
]:
    """Convenience decorator using the global API cache.

    Args:
        ttl: Time-to-live in seconds. Uses default (300s) if None.

    Example:
        @cached(ttl=600)
        async def search_api(query: str) -> list:
            ...
    """
    return api_cache.cached(ttl=ttl)


def get_cache_stats() -> CacheStats:
    """Get statistics from the global API cache."""
    return api_cache.stats


async def clear_cache() -> None:
    """Clear the global API cache."""
    await api_cache.clear()
