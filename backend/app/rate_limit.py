import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

# In-memory per-process sliding-window rate limiter. Good enough for a
# single-instance deployment; resets on restart and doesn't share state
# across workers, but that's an acceptable tradeoff for blunting
# brute-force/forged-auth attempts on login endpoints without adding a
# Redis dependency.
_hits: dict[tuple[str, str], deque] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(bucket: str, limit: int, window_seconds: int):
    """FastAPI dependency: at most `limit` requests per `window_seconds` per
    client IP, within a given named `bucket` (so different endpoints don't
    share a budget)."""

    def dependency(request: Request) -> None:
        key = (bucket, _client_ip(request))
        now = time.monotonic()
        hits = _hits[key]
        while hits and now - hits[0] > window_seconds:
            hits.popleft()
        if len(hits) >= limit:
            raise HTTPException(429, "Too many requests, try again later")
        hits.append(now)

    return dependency
