"""Rate limiting engine with Redis backend and in-memory fallback."""

import asyncio
import time

from app.core.errors import RateLimitExceededError


class RateLimiter:
    """Token bucket / sliding window rate limiter."""

    def __init__(self):
        # In-memory storage: key -> (tokens, last_update_timestamp)
        self._memory_store: dict[str, tuple[float, float]] = {}

    def check(self, key: str, max_requests: int = 60, window_seconds: int = 60) -> bool:
        """
        Check and consume 1 token for the specified key.
        Raises RateLimitExceededError if rate exceeded.
        """
        now = time.time()
        fill_rate = max_requests / window_seconds

        tokens, last_update = self._memory_store.get(key, (float(max_requests), now))
        # Add elapsed tokens
        elapsed = now - last_update
        tokens = min(float(max_requests), tokens + elapsed * fill_rate)

        if tokens >= 1.0:
            tokens -= 1.0
            self._memory_store[key] = (tokens, now)
            return True
        else:
            self._memory_store[key] = (tokens, now)
            raise RateLimitExceededError(
                f"Rate limit exceeded: max {max_requests} requests per {window_seconds}s"
            )

    async def acquire_or_wait(
        self,
        key: str,
        max_requests: float = 8.0,
        window_seconds: float = 1.0,
        max_wait_seconds: float = 5.0,
    ) -> bool:
        """
        Acquire 1 token, waiting if necessary up to max_wait_seconds.
        Used for polite rate-limited API consumers like SEC EDGAR (<= 10 req/s).
        """
        start = time.time()
        fill_rate = max_requests / window_seconds

        while time.time() - start < max_wait_seconds:
            now = time.time()
            tokens, last_update = self._memory_store.get(key, (float(max_requests), now))
            elapsed = now - last_update
            tokens = min(float(max_requests), tokens + elapsed * fill_rate)

            if tokens >= 1.0:
                tokens -= 1.0
                self._memory_store[key] = (tokens, now)
                return True

            wait_needed = (1.0 - tokens) / fill_rate
            await asyncio.sleep(min(wait_needed, 0.2))

        raise RateLimitExceededError(
            f"Rate limit throttle timed out waiting for {key} ({max_requests} req / {window_seconds}s)"
        )


# Global rate limiter instance
limiter = RateLimiter()
