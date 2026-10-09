"""HTTP access-log middleware (``http_access`` per request)."""

import logging
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.observability.events import HttpLogEvent


_SKIP_OR_DEBUG = {"/health", "/favicon.ico"}

logger = logging.getLogger(__name__)


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Emit ``http_access`` with method, path, status, and duration after each response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time

        log_fn = logger.debug if request.url.path in _SKIP_OR_DEBUG else logger.info
        log_fn(
            "%s method=%s path=%s status=%s duration_ms=%.1f",
            HttpLogEvent.HTTP_ACCESS,
            request.method,
            request.url.path,
            response.status_code,
            process_time * 1000,
        )

        return response
