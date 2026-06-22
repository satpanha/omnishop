"""
In-memory Token Bucket Rate Limiting Middleware.
Per-IP limits:
  - Auth routes: 10 requests per minute
  - All other routes: 60 requests per minute
"""

import time
from typing import Dict, Tuple
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, cleanup_interval_seconds: float = 300.0):
        super().__init__(app)
        # Map: IP -> (tokens, last_refill_time)
        self.buckets: Dict[str, Tuple[float, float]] = {}
        self.cleanup_interval = cleanup_interval_seconds
        self.last_cleanup = time.time()

    def _cleanup_stale_entries(self):
        """Periodically clean up bucket entries to prevent memory growth."""
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return
        
        # Remove entries that have had full tokens for over 10 minutes
        stale_ips = []
        for ip, (tokens, last_refill) in self.buckets.items():
            if now - last_refill > 600:
                stale_ips.append(ip)

        for ip in stale_ips:
            del self.buckets[ip]
        self.last_cleanup = now

    def _allow_request(self, ip: str, path: str) -> bool:
        """
        Check if request is allowed under rate limits using token bucket algorithm.
        """
        now = time.time()
        self._cleanup_stale_entries()

        # Determine limit rules based on path
        is_auth = "/auth" in path
        rate = 10.0 if is_auth else 60.0  # requests per minute
        capacity = 10.0 if is_auth else 60.0

        refill_rate = rate / 60.0  # tokens per second

        if ip not in self.buckets:
            self.buckets[ip] = (capacity - 1.0, now)
            return True

        tokens, last_refill = self.buckets[ip]
        
        # Calculate new tokens
        elapsed = now - last_refill
        new_tokens = tokens + (elapsed * refill_rate)
        if new_tokens > capacity:
            new_tokens = capacity

        # Determine if we can consume a token
        if new_tokens >= 1.0:
            self.buckets[ip] = (new_tokens - 1.0, now)
            return True
        else:
            self.buckets[ip] = (new_tokens, now)
            return False

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Bypass preflight OPTIONS requests
        if request.method == "OPTIONS":
            return await call_next(request)

        # Bypass health check endpoints or static doc routes if needed
        if request.url.path in ["/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)

        # Retrieve client IP
        client_ip = request.client.host if request.client else "unknown_ip"
        
        # Check rate limit
        if not self._allow_request(client_ip, request.url.path):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Please try again later."},
            )

        return await call_next(request)
