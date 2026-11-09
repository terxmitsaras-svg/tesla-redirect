"""Small in-process sliding-window rate limiter.

Adequate for a single API instance. For multiple instances, swap for a Redis-backed limiter
(same interface) — see docs/DEPLOYMENT.md.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class RateLimiter:
    def __init__(self, limit: int, window_seconds: float):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> bool:
        now = time.monotonic()
        q = self._hits[key]
        while q and q[0] <= now - self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True

    def enforce(self, key: str) -> None:
        if not self.check(key):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Rate limit exceeded, slow down.")

    def reset(self) -> None:
        self._hits.clear()


auth_limiter = RateLimiter(limit=10, window_seconds=60)
run_limiter = RateLimiter(limit=20, window_seconds=60)
ws_message_limiter = RateLimiter(limit=60, window_seconds=60)


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"
