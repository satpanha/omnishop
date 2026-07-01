"""
Correlation ID middleware.

Threads a per-request correlation ID through every log line emitted during that
request so checkout→payway→callback→notification events can be traced together.
The ID is propagated in the ``X-Correlation-ID`` HTTP header (inbound and outbound).
"""
from __future__ import annotations

import contextvars
import logging
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)


def get_correlation_id() -> str:
    return _correlation_id.get()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        token = _correlation_id.set(cid)
        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = cid
            return response
        finally:
            _correlation_id.reset(token)


class CorrelationIdFilter(logging.Filter):
    """Inject correlation_id into every log record in this request context."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or "-"  # type: ignore[attr-defined]
        return True
