"""
Rate Limiting Middleware - API Protection
Prevents abuse and ensures fair usage of API resources
"""

from typing import Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from loguru import logger


class RateLimiter:
    """
    In-memory rate limiter for API endpoints.

    Implements token bucket algorithm for rate limiting.
    For production, use Redis-based rate limiting.
    """

    def __init__(self):
        """Initialize rate limiter with in-memory storage."""
        # Storage: {identifier: {"tokens": int, "last_update": datetime, "requests": []}}
        self.storage = defaultdict(lambda: {
            "tokens": 0,
            "last_update": datetime.utcnow(),
            "requests": []
        })

        # Lock for thread-safe operations
        self.lock = asyncio.Lock()

        logger.info("✅ Rate Limiter initialized (in-memory)")

    async def is_rate_limited(
        self,
        identifier: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple[bool, dict]:
        """
        Check if identifier is rate limited.

        Args:
            identifier: Unique identifier (IP, user_id, etc.)
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_limited, info_dict)
        """
        async with self.lock:
            now = datetime.utcnow()
            user_data = self.storage[identifier]

            # Remove old requests outside the window
            cutoff_time = now - timedelta(seconds=window_seconds)
            user_data["requests"] = [
                req_time for req_time in user_data["requests"]
                if req_time > cutoff_time
            ]

            # Check if limit exceeded
            current_count = len(user_data["requests"])

            if current_count >= max_requests:
                # Calculate when they can retry
                oldest_request = user_data["requests"][0]
                retry_after = int((oldest_request + timedelta(seconds=window_seconds) - now).total_seconds())

                return True, {
                    "limited": True,
                    "current_count": current_count,
                    "max_requests": max_requests,
                    "window_seconds": window_seconds,
                    "retry_after": max(retry_after, 1)
                }

            # Add current request
            user_data["requests"].append(now)
            user_data["last_update"] = now

            remaining = max_requests - (current_count + 1)

            return False, {
                "limited": False,
                "current_count": current_count + 1,
                "max_requests": max_requests,
                "remaining": remaining,
                "window_seconds": window_seconds,
                "reset_at": (now + timedelta(seconds=window_seconds)).isoformat()
            }

    async def cleanup_old_entries(self, max_age_hours: int = 24):
        """
        Clean up old entries to prevent memory bloat.

        Args:
            max_age_hours: Remove entries older than this many hours
        """
        async with self.lock:
            now = datetime.utcnow()
            cutoff = now - timedelta(hours=max_age_hours)

            to_remove = []
            for identifier, data in self.storage.items():
                if data["last_update"] < cutoff:
                    to_remove.append(identifier)

            for identifier in to_remove:
                del self.storage[identifier]

            if to_remove:
                logger.info(f"🧹 Cleaned up {len(to_remove)} old rate limit entries")


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


# ============================================================================
# RATE LIMIT DECORATORS & MIDDLEWARE
# ============================================================================

def rate_limit(
    max_requests: int = 60,
    window_seconds: int = 60,
    identifier: Optional[Callable] = None
):
    """
    Decorator for rate limiting endpoints.

    Args:
        max_requests: Maximum requests allowed
        window_seconds: Time window in seconds
        identifier: Function to extract identifier from request (default: IP address)

    Example:
        @app.get("/api/endpoint")
        @rate_limit(max_requests=10, window_seconds=60)
        async def endpoint(request: Request):
            return {"message": "success"}
    """

    def decorator(func):
        async def wrapper(*args, request: Request = None, **kwargs):
            # Extract request if not provided
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request is None:
                # If still no request, skip rate limiting
                logger.warning("Rate limiting skipped: no Request object found")
                return await func(*args, **kwargs)

            # Get identifier (IP address by default)
            if identifier:
                key = identifier(request)
            else:
                key = request.client.host if request.client else "unknown"

            # Check rate limit
            limiter = get_rate_limiter()
            is_limited, info = await limiter.is_rate_limited(
                identifier=key,
                max_requests=max_requests,
                window_seconds=window_seconds
            )

            if is_limited:
                logger.warning(
                    f"⛔ Rate limit exceeded for {key}: "
                    f"{info['current_count']}/{info['max_requests']} requests"
                )

                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"Too many requests. Try again in {info['retry_after']} seconds.",
                        "retry_after": info["retry_after"],
                        "limit": info["max_requests"],
                        "window": info["window_seconds"]
                    },
                    headers={
                        "Retry-After": str(info["retry_after"]),
                        "X-RateLimit-Limit": str(info["max_requests"]),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(datetime.utcnow().timestamp()) + info["retry_after"])
                    }
                )

            # Execute endpoint
            response = await func(*args, **kwargs)

            # Add rate limit headers to response
            if isinstance(response, JSONResponse):
                response.headers["X-RateLimit-Limit"] = str(info["max_requests"])
                response.headers["X-RateLimit-Remaining"] = str(info.get("remaining", 0))
                response.headers["X-RateLimit-Reset"] = str(
                    int(datetime.utcnow().timestamp()) + info["window_seconds"]
                )

            return response

        return wrapper

    return decorator


# ============================================================================
# RATE LIMIT TIERS
# ============================================================================

# Tier definitions
RATE_LIMITS = {
    "free": {
        "requests_per_minute": 20,
        "requests_per_hour": 100,
        "requests_per_day": 1000,
    },
    "personal": {
        "requests_per_minute": 60,
        "requests_per_hour": 1000,
        "requests_per_day": 10000,
    },
    "professional": {
        "requests_per_minute": 120,
        "requests_per_hour": 5000,
        "requests_per_day": 50000,
    },
    "enterprise": {
        "requests_per_minute": 300,
        "requests_per_hour": 20000,
        "requests_per_day": 200000,
    },
}


def get_user_rate_limit(user_tier: str = "free") -> dict:
    """
    Get rate limit configuration for user tier.

    Args:
        user_tier: User's subscription tier

    Returns:
        Rate limit configuration
    """
    return RATE_LIMITS.get(user_tier, RATE_LIMITS["free"])


# ============================================================================
# FASTAPI MIDDLEWARE
# ============================================================================

class RateLimitMiddleware:
    """
    Middleware for global rate limiting.

    Apply to all endpoints or specific routes.
    """

    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60,
        exclude_paths: Optional[list[str]] = None
    ):
        """
        Initialize rate limit middleware.

        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
            exclude_paths: Paths to exclude from rate limiting
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/redoc", "/openapi.json"]
        self.limiter = get_rate_limiter()

        logger.info(
            f"🛡️  Rate Limit Middleware initialized: "
            f"{max_requests} requests per {window_seconds}s"
        )

    async def __call__(self, request: Request, call_next):
        """Process request with rate limiting."""

        # Skip excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Get identifier (IP address)
        identifier = request.client.host if request.client else "unknown"

        # Check rate limit
        is_limited, info = await self.limiter.is_rate_limited(
            identifier=identifier,
            max_requests=self.max_requests,
            window_seconds=self.window_seconds
        )

        if is_limited:
            logger.warning(
                f"⛔ Rate limit exceeded for {identifier} on {request.url.path}: "
                f"{info['current_count']}/{info['max_requests']} requests"
            )

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Try again in {info['retry_after']} seconds.",
                    "retry_after": info["retry_after"],
                    "limit": info["max_requests"],
                    "window": info["window_seconds"]
                },
                headers={
                    "Retry-After": str(info["retry_after"]),
                    "X-RateLimit-Limit": str(info["max_requests"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(datetime.utcnow().timestamp()) + info["retry_after"])
                }
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(info["max_requests"])
        response.headers["X-RateLimit-Remaining"] = str(info.get("remaining", 0))
        response.headers["X-RateLimit-Reset"] = str(
            int(datetime.utcnow().timestamp()) + info["window_seconds"]
        )

        return response


# ============================================================================
# USER-SPECIFIC RATE LIMITING
# ============================================================================

async def check_user_rate_limit(request: Request, user_id: str, tier: str = "free") -> bool:
    """
    Check user-specific rate limit based on subscription tier.

    Args:
        request: FastAPI request object
        user_id: User's unique ID
        tier: User's subscription tier

    Returns:
        True if allowed, raises HTTPException if limited

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    limits = get_user_rate_limit(tier)
    limiter = get_rate_limiter()

    # Check minute limit
    is_limited, info = await limiter.is_rate_limited(
        identifier=f"user:{user_id}:minute",
        max_requests=limits["requests_per_minute"],
        window_seconds=60
    )

    if is_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "message": f"Minute limit exceeded ({limits['requests_per_minute']} req/min). Upgrade for higher limits.",
                "retry_after": info["retry_after"],
                "tier": tier,
                "upgrade_url": "/api/v1/subscription/upgrade"
            }
        )

    return True
