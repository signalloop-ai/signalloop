from collections import defaultdict, deque
from time import monotonic
from typing import Deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class InMemoryRateLimiter:
    def __init__(self, *, max_requests: int, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = monotonic()
        cutoff = now - self.window_seconds
        seen = self.requests[key]
        while seen and seen[0] < cutoff:
            seen.popleft()
        if len(seen) >= self.max_requests:
            return False
        seen.append(now)
        return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, max_requests: int, enabled: bool = True) -> None:
        super().__init__(app)
        self.enabled = enabled
        self.limiter = InMemoryRateLimiter(max_requests=max_requests)

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self.enabled or request.url.path == "/health":
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        key = f"{client_host}:{request.method}:{request.url.path}"
        if not self.limiter.allow(key):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please wait and retry."},
                headers={"Retry-After": "60"},
            )
        return await call_next(request)
