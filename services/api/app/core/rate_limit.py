"""
Sliding-window rate limiter (README: "Sliding window / token bucket").

In-process implementation for a single API replica and tests. Multi-replica
deployments swap in a Redis-backed limiter with the same interface.
"""

import asyncio
import time
from collections import defaultdict, deque
from typing import Protocol


class RateLimiter(Protocol):
    async def hit(self, key: str, limit: int, window_seconds: float) -> bool:
        """Record one event for `key`; return False if the limit is exceeded."""
        ...

    async def reset(self, key: str) -> None: ...


class InMemorySlidingWindowLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def hit(self, key: str, limit: int, window_seconds: float) -> bool:
        now = time.monotonic()
        async with self._lock:
            events = self._events[key]
            while events and events[0] <= now - window_seconds:
                events.popleft()
            if len(events) >= limit:
                return False
            events.append(now)
            return True

    async def reset(self, key: str) -> None:
        async with self._lock:
            self._events.pop(key, None)
