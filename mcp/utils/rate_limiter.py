"""
Token-bucket rate limiter shared across all tools.
Prevents hitting external API limits by throttling calls per tool.

Usage:
    from tools.utils.rate_limiter import rate_limiter

    # In your tool function:
    await rate_limiter.acquire("duckduckgo")   # waits if limit is reached
    await rate_limiter.acquire("gmail")
"""

import asyncio
import time
from dataclasses import dataclass, field
from utils.exceptions import RateLimitError


LIMITS: dict[str, float] = {
    "gmail":       0.5,   
    "duckduckgo":  1.0,   
    "stt":         2.0,
    "calendar":    1.0, 
    "default":     1.0,  
}


@dataclass
class _Bucket:
    calls_per_second: float
    tokens:           float = field(init=False)
    last_refill:      float = field(init=False)
    lock:             asyncio.Lock = field(default_factory=asyncio.Lock)

    def __post_init__(self):
        self.tokens      = self.calls_per_second
        self.last_refill = time.monotonic()

    def _refill(self) -> None:
        now     = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens      = min(self.calls_per_second, self.tokens + elapsed * self.calls_per_second)
        self.last_refill = now

    async def acquire(self, tool_name: str, hard_fail: bool = False) -> None:
        """
        Consume one token.
        - If hard_fail=True  → raises RateLimitError immediately when empty.
        - If hard_fail=False → waits until a token is available (default).
        """
        async with self.lock:
            self._refill()
            if self.tokens >= 1:
                self.tokens -= 1
                return

            if hard_fail:
                wait = (1 - self.tokens) / self.calls_per_second
                raise RateLimitError(tool_name=tool_name, retry_after=int(wait) + 1)

            # Wait for next token
            wait = (1 - self.tokens) / self.calls_per_second
            await asyncio.sleep(wait)
            self._refill()
            self.tokens -= 1


class RateLimiter:
    def __init__(self):
        self._buckets: dict[str, _Bucket] = {}

    def _get_bucket(self, tool_name: str) -> _Bucket:
        if tool_name not in self._buckets:
            rate = LIMITS.get(tool_name, LIMITS["default"])
            self._buckets[tool_name] = _Bucket(calls_per_second=rate)
        return self._buckets[tool_name]

    async def acquire(self, tool_name: str, hard_fail: bool = False) -> None:
        """Call this at the start of any tool that hits an external API."""
        bucket = self._get_bucket(tool_name)
        await bucket.acquire(tool_name, hard_fail=hard_fail)

    def remaining_tokens(self, tool_name: str) -> float:
        """Useful for debugging or status endpoints."""
        bucket = self._get_bucket(tool_name)
        bucket._refill()
        return round(bucket.tokens, 2)


rate_limiter = RateLimiter()