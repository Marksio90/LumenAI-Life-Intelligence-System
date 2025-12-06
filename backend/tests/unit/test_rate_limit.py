"""
Unit tests for Rate Limiting Middleware
"""

import pytest
import asyncio
from datetime import datetime, timedelta

from middleware.rate_limit_middleware import RateLimiter, get_user_rate_limit


class TestRateLimiter:
    """Test rate limiter functionality."""

    @pytest.fixture
    def rate_limiter(self):
        """Create fresh rate limiter instance."""
        return RateLimiter()

    @pytest.mark.asyncio
    async def test_first_request_allowed(self, rate_limiter):
        """Test that first request is always allowed."""
        identifier = "test_user_1"
        is_limited, info = await rate_limiter.is_rate_limited(
            identifier=identifier,
            max_requests=10,
            window_seconds=60
        )

        assert is_limited is False
        assert info["limited"] is False
        assert info["current_count"] == 1
        assert info["remaining"] == 9

    @pytest.mark.asyncio
    async def test_multiple_requests_within_limit(self, rate_limiter):
        """Test multiple requests within rate limit."""
        identifier = "test_user_2"
        max_requests = 5

        for i in range(max_requests):
            is_limited, info = await rate_limiter.is_rate_limited(
                identifier=identifier,
                max_requests=max_requests,
                window_seconds=60
            )

            assert is_limited is False
            assert info["current_count"] == i + 1
            assert info["remaining"] == max_requests - (i + 1)

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, rate_limiter):
        """Test that requests are blocked after limit."""
        identifier = "test_user_3"
        max_requests = 3

        # Make max_requests
        for _ in range(max_requests):
            await rate_limiter.is_rate_limited(
                identifier=identifier,
                max_requests=max_requests,
                window_seconds=60
            )

        # Next request should be limited
        is_limited, info = await rate_limiter.is_rate_limited(
            identifier=identifier,
            max_requests=max_requests,
            window_seconds=60
        )

        assert is_limited is True
        assert info["limited"] is True
        assert info["current_count"] == max_requests
        assert "retry_after" in info
        assert info["retry_after"] > 0

    @pytest.mark.asyncio
    async def test_window_reset(self, rate_limiter):
        """Test that rate limit resets after window expires."""
        identifier = "test_user_4"
        max_requests = 2
        window_seconds = 1  # 1 second window

        # Exceed limit
        for _ in range(max_requests):
            await rate_limiter.is_rate_limited(
                identifier=identifier,
                max_requests=max_requests,
                window_seconds=window_seconds
            )

        # Should be limited
        is_limited, _ = await rate_limiter.is_rate_limited(
            identifier=identifier,
            max_requests=max_requests,
            window_seconds=window_seconds
        )
        assert is_limited is True

        # Wait for window to expire
        await asyncio.sleep(window_seconds + 0.1)

        # Should be allowed again
        is_limited, info = await rate_limiter.is_rate_limited(
            identifier=identifier,
            max_requests=max_requests,
            window_seconds=window_seconds
        )
        assert is_limited is False
        assert info["current_count"] == 1

    @pytest.mark.asyncio
    async def test_different_users_independent(self, rate_limiter):
        """Test that different users have independent rate limits."""
        max_requests = 2
        window_seconds = 60

        # User 1 exceeds limit
        for _ in range(max_requests):
            await rate_limiter.is_rate_limited(
                identifier="user_1",
                max_requests=max_requests,
                window_seconds=window_seconds
            )

        is_limited_1, _ = await rate_limiter.is_rate_limited(
            identifier="user_1",
            max_requests=max_requests,
            window_seconds=window_seconds
        )
        assert is_limited_1 is True

        # User 2 should still be allowed
        is_limited_2, info_2 = await rate_limiter.is_rate_limited(
            identifier="user_2",
            max_requests=max_requests,
            window_seconds=window_seconds
        )
        assert is_limited_2 is False
        assert info_2["current_count"] == 1

    @pytest.mark.asyncio
    async def test_cleanup_old_entries(self, rate_limiter):
        """Test cleanup of old entries."""
        identifier = "test_user_5"

        # Add entry
        await rate_limiter.is_rate_limited(
            identifier=identifier,
            max_requests=10,
            window_seconds=60
        )

        assert identifier in rate_limiter.storage

        # Cleanup old entries (0 hours = cleanup everything)
        await rate_limiter.cleanup_old_entries(max_age_hours=0)

        # Entry should still be there (just created)
        assert identifier in rate_limiter.storage


class TestRateLimitTiers:
    """Test rate limit tier configurations."""

    def test_free_tier_limits(self):
        """Test free tier rate limits."""
        limits = get_user_rate_limit("free")

        assert limits["requests_per_minute"] == 20
        assert limits["requests_per_hour"] == 100
        assert limits["requests_per_day"] == 1000

    def test_personal_tier_limits(self):
        """Test personal tier rate limits."""
        limits = get_user_rate_limit("personal")

        assert limits["requests_per_minute"] == 60
        assert limits["requests_per_hour"] == 1000
        assert limits["requests_per_day"] == 10000

    def test_professional_tier_limits(self):
        """Test professional tier rate limits."""
        limits = get_user_rate_limit("professional")

        assert limits["requests_per_minute"] == 120
        assert limits["requests_per_hour"] == 5000
        assert limits["requests_per_day"] == 50000

    def test_enterprise_tier_limits(self):
        """Test enterprise tier rate limits."""
        limits = get_user_rate_limit("enterprise")

        assert limits["requests_per_minute"] == 300
        assert limits["requests_per_hour"] == 20000
        assert limits["requests_per_day"] == 200000

    def test_unknown_tier_defaults_to_free(self):
        """Test that unknown tiers default to free."""
        limits = get_user_rate_limit("unknown_tier")

        assert limits == get_user_rate_limit("free")

    def test_tier_hierarchy(self):
        """Test that higher tiers have higher limits."""
        free = get_user_rate_limit("free")
        personal = get_user_rate_limit("personal")
        professional = get_user_rate_limit("professional")
        enterprise = get_user_rate_limit("enterprise")

        assert personal["requests_per_minute"] > free["requests_per_minute"]
        assert professional["requests_per_minute"] > personal["requests_per_minute"]
        assert enterprise["requests_per_minute"] > professional["requests_per_minute"]
