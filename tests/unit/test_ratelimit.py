"""Unit tests for RateLimiter and polite throttling."""

import pytest
from app.core.errors import RateLimitExceededError
from app.core.ratelimit import RateLimiter


def test_rate_limiter_check():
    limiter = RateLimiter()
    # Consume 2 tokens
    assert limiter.check("test-key", max_requests=2, window_seconds=60) is True
    assert limiter.check("test-key", max_requests=2, window_seconds=60) is True

    # 3rd token must raise RateLimitExceededError
    with pytest.raises(RateLimitExceededError):
        limiter.check("test-key", max_requests=2, window_seconds=60)


@pytest.mark.asyncio
async def test_rate_limiter_acquire_or_wait():
    limiter = RateLimiter()
    # Acquire token
    acquired = await limiter.acquire_or_wait(
        "sec-edgar-test", max_requests=5.0, window_seconds=1.0
    )
    assert acquired is True
