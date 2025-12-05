"""
Multi-Level Caching Service with Redis

Implements L1 (in-memory) and L2 (Redis) caching for optimal performance.
"""

import asyncio
import logging
import hashlib
import pickle
from typing import Any, Optional, Callable, Union
from datetime import timedelta
from functools import wraps
import json

import redis.asyncio as redis
from cachetools import TTLCache, LRUCache

logger = logging.getLogger(__name__)


class CacheService:
    """
    Multi-level caching service.

    Features:
    - L1 Cache: In-memory LRU/TTL cache (fastest, per-instance)
    - L2 Cache: Redis distributed cache (shared across instances)
    - Cache invalidation
    - Cache warming
    - Metrics and monitoring
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        l1_max_size: int = 1000,
        l1_ttl: int = 300,  # 5 minutes
        l2_default_ttl: int = 3600,  # 1 hour
    ):
        # L1 Cache (in-memory)
        self.l1_cache = TTLCache(maxsize=l1_max_size, ttl=l1_ttl)
        self.l1_ttl = l1_ttl

        # L2 Cache (Redis)
        self.redis_client: Optional[redis.Redis] = None
        self.redis_url = redis_url
        self.l2_default_ttl = l2_default_ttl

        # Metrics
        self.metrics = {
            "l1_hits": 0,
            "l1_misses": 0,
            "l2_hits": 0,
            "l2_misses": 0,
            "sets": 0,
            "deletes": 0,
        }

        logger.info(
            f"CacheService initialized: L1_size={l1_max_size}, "
            f"L1_ttl={l1_ttl}s, L2_ttl={l2_default_ttl}s"
        )

    async def _get_redis_client(self) -> Optional[redis.Redis]:
        """Lazy initialization of Redis client."""
        if not self.redis_client:
            try:
                import os
                redis_host = os.getenv("REDIS_HOST", "localhost")
                redis_port = int(os.getenv("REDIS_PORT", "6379"))
                redis_db = int(os.getenv("REDIS_CACHE_DB", "2"))

                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    decode_responses=False,
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                )

                # Test connection
                await self.redis_client.ping()
                logger.info(f"Redis connected: {redis_host}:{redis_port}/{redis_db}")

            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self.redis_client = None

        return self.redis_client

    def _generate_key(self, key: Union[str, tuple]) -> str:
        """
        Generate cache key from string or tuple.

        Args:
            key: Cache key (string or tuple)

        Returns:
            String cache key
        """
        if isinstance(key, str):
            return key

        # Hash tuple/complex key
        key_str = str(key)
        return hashlib.md5(key_str.encode()).hexdigest()

    async def get(
        self,
        key: Union[str, tuple],
        use_l1: bool = True,
        use_l2: bool = True,
    ) -> Optional[Any]:
        """
        Get value from cache (L1 -> L2).

        Args:
            key: Cache key
            use_l1: Whether to check L1 cache
            use_l2: Whether to check L2 cache

        Returns:
            Cached value or None
        """
        cache_key = self._generate_key(key)

        # Try L1 cache first
        if use_l1:
            if cache_key in self.l1_cache:
                self.metrics["l1_hits"] += 1
                logger.debug(f"L1 cache HIT: {cache_key}")
                return self.l1_cache[cache_key]
            else:
                self.metrics["l1_misses"] += 1

        # Try L2 cache (Redis)
        if use_l2:
            redis_client = await self._get_redis_client()
            if redis_client:
                try:
                    value = await redis_client.get(cache_key)
                    if value is not None:
                        self.metrics["l2_hits"] += 1
                        logger.debug(f"L2 cache HIT: {cache_key}")

                        # Deserialize
                        deserialized = pickle.loads(value)

                        # Populate L1 cache
                        if use_l1:
                            self.l1_cache[cache_key] = deserialized

                        return deserialized
                    else:
                        self.metrics["l2_misses"] += 1
                except Exception as e:
                    logger.error(f"Redis GET error: {e}")

        logger.debug(f"Cache MISS: {cache_key}")
        return None

    async def set(
        self,
        key: Union[str, tuple],
        value: Any,
        ttl: Optional[int] = None,
        use_l1: bool = True,
        use_l2: bool = True,
    ) -> bool:
        """
        Set value in cache (L1 and/or L2).

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None = default)
            use_l1: Whether to set in L1 cache
            use_l2: Whether to set in L2 cache

        Returns:
            Success status
        """
        cache_key = self._generate_key(key)
        ttl = ttl or self.l2_default_ttl

        # Set in L1 cache
        if use_l1:
            self.l1_cache[cache_key] = value

        # Set in L2 cache (Redis)
        if use_l2:
            redis_client = await self._get_redis_client()
            if redis_client:
                try:
                    # Serialize
                    serialized = pickle.dumps(value)

                    # Set with TTL
                    await redis_client.setex(
                        cache_key,
                        ttl,
                        serialized
                    )
                except Exception as e:
                    logger.error(f"Redis SET error: {e}")
                    return False

        self.metrics["sets"] += 1
        logger.debug(f"Cache SET: {cache_key}, ttl={ttl}s")
        return True

    async def delete(
        self,
        key: Union[str, tuple],
        use_l1: bool = True,
        use_l2: bool = True,
    ) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key
            use_l1: Whether to delete from L1 cache
            use_l2: Whether to delete from L2 cache

        Returns:
            Success status
        """
        cache_key = self._generate_key(key)

        # Delete from L1
        if use_l1 and cache_key in self.l1_cache:
            del self.l1_cache[cache_key]

        # Delete from L2
        if use_l2:
            redis_client = await self._get_redis_client()
            if redis_client:
                try:
                    await redis_client.delete(cache_key)
                except Exception as e:
                    logger.error(f"Redis DELETE error: {e}")
                    return False

        self.metrics["deletes"] += 1
        logger.debug(f"Cache DELETE: {cache_key}")
        return True

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching pattern (L2 only).

        Args:
            pattern: Pattern to match (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        redis_client = await self._get_redis_client()
        if not redis_client:
            return 0

        try:
            # Find matching keys
            keys = []
            async for key in redis_client.scan_iter(match=pattern):
                keys.append(key)

            # Delete keys
            if keys:
                deleted = await redis_client.delete(*keys)
                logger.info(f"Invalidated {deleted} keys matching: {pattern}")
                return deleted

            return 0

        except Exception as e:
            logger.error(f"Pattern invalidation error: {e}")
            return 0

    async def get_or_set(
        self,
        key: Union[str, tuple],
        factory: Callable,
        ttl: Optional[int] = None,
    ) -> Any:
        """
        Get from cache or compute and set.

        Args:
            key: Cache key
            factory: Async function to compute value if not cached
            ttl: Time to live in seconds

        Returns:
            Cached or computed value
        """
        # Try to get from cache
        value = await self.get(key)

        if value is not None:
            return value

        # Compute value
        if asyncio.iscoroutinefunction(factory):
            value = await factory()
        else:
            value = factory()

        # Set in cache
        await self.set(key, value, ttl=ttl)

        return value

    def clear_l1(self):
        """Clear L1 cache."""
        self.l1_cache.clear()
        logger.info("L1 cache cleared")

    async def clear_l2(self):
        """Clear L2 cache (all keys)."""
        redis_client = await self._get_redis_client()
        if redis_client:
            try:
                await redis_client.flushdb()
                logger.info("L2 cache cleared")
            except Exception as e:
                logger.error(f"L2 cache clear error: {e}")

    async def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Statistics dictionary
        """
        stats = {
            "l1_size": len(self.l1_cache),
            "l1_max_size": self.l1_cache.maxsize,
            "l1_hit_rate": self._calculate_hit_rate("l1"),
            "l2_hit_rate": self._calculate_hit_rate("l2"),
            **self.metrics,
        }

        # Get L2 stats from Redis
        redis_client = await self._get_redis_client()
        if redis_client:
            try:
                info = await redis_client.info("stats")
                stats["l2_keys"] = await redis_client.dbsize()
                stats["l2_hits_total"] = info.get("keyspace_hits", 0)
                stats["l2_misses_total"] = info.get("keyspace_misses", 0)
            except Exception as e:
                logger.error(f"Redis stats error: {e}")

        return stats

    def _calculate_hit_rate(self, level: str) -> float:
        """Calculate hit rate for cache level."""
        if level == "l1":
            total = self.metrics["l1_hits"] + self.metrics["l1_misses"]
            return self.metrics["l1_hits"] / total if total > 0 else 0.0
        elif level == "l2":
            total = self.metrics["l2_hits"] + self.metrics["l2_misses"]
            return self.metrics["l2_hits"] / total if total > 0 else 0.0
        return 0.0


# Decorator for caching function results
def cached(
    ttl: int = 3600,
    key_prefix: str = "",
    use_l1: bool = True,
    use_l2: bool = True,
):
    """
    Decorator to cache function results.

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
        use_l1: Use L1 cache
        use_l2: Use L2 cache

    Example:
        @cached(ttl=300, key_prefix="user")
        async def get_user(user_id: str):
            return await db.get_user(user_id)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_service = get_cache_service()

            # Generate cache key
            key_parts = [key_prefix, func.__name__]
            if args:
                key_parts.extend(str(arg) for arg in args)
            if kwargs:
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))

            cache_key = ":".join(key_parts)

            # Try to get from cache
            cached_value = await cache_service.get(
                cache_key,
                use_l1=use_l1,
                use_l2=use_l2
            )

            if cached_value is not None:
                return cached_value

            # Compute value
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Set in cache
            await cache_service.set(
                cache_key,
                result,
                ttl=ttl,
                use_l1=use_l1,
                use_l2=use_l2
            )

            return result

        return wrapper
    return decorator


# Global instance
_cache_service = None


def get_cache_service() -> CacheService:
    """Get or create the global CacheService instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
