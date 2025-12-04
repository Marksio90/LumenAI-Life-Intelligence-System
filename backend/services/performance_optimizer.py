"""
Performance Optimization Module
Caching, rate limiting, and performance enhancements for agents
"""

from typing import Any, Optional, Callable, Dict
from functools import wraps, lru_cache
from datetime import datetime, timedelta
import hashlib
import json
import asyncio
from loguru import logger


class CacheManager:
    """
    Smart caching system for agent responses and API calls
    """

    def __init__(self, default_ttl: int = 300):
        """
        Args:
            default_ttl: Default time-to-live in seconds (5 minutes)
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }

    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_data = {
            "args": str(args),
            "kwargs": str(sorted(kwargs.items()))
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key not in self._cache:
            self.stats["misses"] += 1
            return None

        entry = self._cache[key]
        if datetime.now() > entry["expires_at"]:
            # Expired
            del self._cache[key]
            self.stats["evictions"] += 1
            self.stats["misses"] += 1
            return None

        self.stats["hits"] += 1
        logger.debug(f"Cache HIT for key {key[:8]}...")
        return entry["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL"""
        ttl = ttl or self.default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl)

        self._cache[key] = {
            "value": value,
            "expires_at": expires_at,
            "created_at": datetime.now()
        }
        logger.debug(f"Cache SET for key {key[:8]}... (TTL: {ttl}s)")

    def invalidate(self, pattern: Optional[str] = None) -> int:
        """
        Invalidate cache entries
        Args:
            pattern: If provided, only invalidate keys containing this pattern
        Returns:
            Number of entries invalidated
        """
        if pattern is None:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache cleared: {count} entries")
            return count

        keys_to_delete = [k for k in self._cache.keys() if pattern in k]
        for key in keys_to_delete:
            del self._cache[key]

        logger.info(f"Cache invalidated: {len(keys_to_delete)} entries matching '{pattern}'")
        return len(keys_to_delete)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0

        return {
            **self.stats,
            "total_requests": total_requests,
            "hit_rate": f"{hit_rate:.2f}%",
            "cache_size": len(self._cache),
            "memory_entries": len(self._cache)
        }

    def cleanup_expired(self) -> int:
        """Remove expired entries"""
        now = datetime.now()
        keys_to_delete = [
            k for k, v in self._cache.items()
            if now > v["expires_at"]
        ]

        for key in keys_to_delete:
            del self._cache[key]

        if keys_to_delete:
            logger.info(f"Cleaned up {len(keys_to_delete)} expired cache entries")

        return len(keys_to_delete)


# Global cache instance
_global_cache = CacheManager()


def cached(ttl: int = 300, cache_instance: Optional[CacheManager] = None):
    """
    Decorator for caching function results

    Args:
        ttl: Time to live in seconds
        cache_instance: Optional custom cache instance

    Example:
        @cached(ttl=600)
        async def expensive_operation(user_id: str):
            # ... expensive work
            return result
    """
    cache = cache_instance or _global_cache

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{func.__name__}:{cache._generate_key(*args, **kwargs)}"

            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            cache.set(cache_key, result, ttl=ttl)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{cache._generate_key(*args, **kwargs)}"

            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)

            return result

        # Return appropriate wrapper based on function type
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


class RateLimiter:
    """
    Rate limiting for API calls and expensive operations
    """

    def __init__(self, max_calls: int, time_window: int):
        """
        Args:
            max_calls: Maximum number of calls allowed
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self._calls: Dict[str, list] = {}

    def is_allowed(self, key: str) -> bool:
        """Check if a call is allowed under rate limit"""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.time_window)

        # Clean old entries
        if key in self._calls:
            self._calls[key] = [
                call_time for call_time in self._calls[key]
                if call_time > cutoff
            ]
        else:
            self._calls[key] = []

        # Check limit
        if len(self._calls[key]) >= self.max_calls:
            logger.warning(f"Rate limit exceeded for {key}")
            return False

        # Record this call
        self._calls[key].append(now)
        return True

    def time_until_allowed(self, key: str) -> float:
        """Get seconds until next call is allowed"""
        if key not in self._calls or len(self._calls[key]) < self.max_calls:
            return 0.0

        oldest_call = min(self._calls[key])
        next_allowed = oldest_call + timedelta(seconds=self.time_window)
        wait_time = (next_allowed - datetime.now()).total_seconds()

        return max(0.0, wait_time)


def rate_limit(max_calls: int, time_window: int):
    """
    Decorator for rate limiting

    Args:
        max_calls: Maximum calls allowed
        time_window: Time window in seconds

    Example:
        @rate_limit(max_calls=10, time_window=60)  # 10 calls per minute
        async def api_call(user_id: str):
            # ... expensive API call
    """
    limiter = RateLimiter(max_calls, time_window)

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Use first argument (usually user_id) as key
            key = str(args[0]) if args else "global"

            if not limiter.is_allowed(key):
                wait_time = limiter.time_until_allowed(key)
                raise Exception(
                    f"Rate limit exceeded. Try again in {wait_time:.1f} seconds."
                )

            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            key = str(args[0]) if args else "global"

            if not limiter.is_allowed(key):
                wait_time = limiter.time_until_allowed(key)
                raise Exception(
                    f"Rate limit exceeded. Try again in {wait_time:.1f} seconds."
                )

            return func(*args, **kwargs)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


class ContextOptimizer:
    """
    Optimizes context management for LLM calls
    Reduces token usage while maintaining relevance
    """

    @staticmethod
    def summarize_conversation(messages: list, max_messages: int = 10) -> list:
        """
        Summarize old conversation to reduce context size

        Args:
            messages: List of conversation messages
            max_messages: Keep this many recent messages in full

        Returns:
            Optimized message list
        """
        if len(messages) <= max_messages:
            return messages

        # Keep recent messages in full
        recent = messages[-max_messages:]

        # Summarize older messages
        old_messages = messages[:-max_messages]
        summary = {
            "role": "system",
            "content": f"[Previous conversation summary: {len(old_messages)} messages exchanged. Key topics discussed.]"
        }

        return [summary] + recent

    @staticmethod
    def extract_relevant_context(
        context: Dict[str, Any],
        relevant_keys: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Extract only relevant context to reduce token usage

        Args:
            context: Full context dictionary
            relevant_keys: Keys to keep (if None, smart selection)

        Returns:
            Filtered context
        """
        if relevant_keys:
            return {k: v for k, v in context.items() if k in relevant_keys}

        # Smart selection based on recency and importance
        important_keys = ["user_id", "current_mood", "recent_events", "preferences"]
        return {k: v for k, v in context.items() if k in important_keys}

    @staticmethod
    def compress_prompt(prompt: str, max_tokens: int = 4000) -> str:
        """
        Compress prompt if too long (rough estimation)

        Args:
            prompt: Original prompt
            max_tokens: Maximum tokens (rough: 1 token ≈ 4 chars)

        Returns:
            Compressed prompt
        """
        max_chars = max_tokens * 4

        if len(prompt) <= max_chars:
            return prompt

        # Keep first and last parts, summarize middle
        keep_chars = max_chars // 2
        return (
            prompt[:keep_chars] +
            "\n\n[... middle section truncated for brevity ...]\n\n" +
            prompt[-keep_chars:]
        )


# Global instances
cache_manager = _global_cache
context_optimizer = ContextOptimizer()


# Utility functions
def get_cache_stats() -> Dict[str, Any]:
    """Get global cache statistics"""
    return _global_cache.get_stats()


def clear_cache(pattern: Optional[str] = None) -> int:
    """Clear global cache"""
    return _global_cache.invalidate(pattern)


def cleanup_expired_cache() -> int:
    """Cleanup expired cache entries"""
    return _global_cache.cleanup_expired()


# Auto-cleanup task (run periodically)
async def auto_cleanup_task(interval: int = 300):
    """
    Background task to cleanup expired cache entries

    Args:
        interval: Cleanup interval in seconds (default: 5 minutes)
    """
    while True:
        await asyncio.sleep(interval)
        try:
            cleaned = cleanup_expired_cache()
            if cleaned > 0:
                logger.info(f"Auto-cleanup: Removed {cleaned} expired entries")
        except Exception as e:
            logger.error(f"Auto-cleanup error: {e}")
