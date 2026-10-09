"""HTTP access-log middleware (``http_access`` per request)."""

import logging
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.observability.events import HttpLogEvent
from app.observability.log_event import log_event


_SKIP_OR_DEBUG = {"/health", "/favicon.ico"}

logger = logging.getLogger(__name__)


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Emit ``http_access`` with method, path, status, and duration after each response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time

        level = logging.DEBUG if request.url.path in _SKIP_OR_DEBUG else logging.INFO
        log_event(
            logger,
            level,
            HttpLogEvent.HTTP_ACCESS,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=f"{process_time * 1000:.1f}",
        )
        return response
