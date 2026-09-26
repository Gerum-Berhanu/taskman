import logging
import time
from uuid import UUID, uuid4
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.request_context import request_id_ctx


_SKIP_OR_DEBUG = {"/health", "/favicon.ico"}

logger = logging.getLogger(__name__)


class AppMiddleware(BaseHTTPMiddleware):
    """Place for shared helpers"""
    pass


def _resolve_request_id(presented_id: str | None) -> UUID:
    """Keep client X-Request-ID only if it is a UUID v4; otherwise generate one."""
    if not presented_id:
        return uuid4()
    try:
        parsed = UUID(presented_id)
    except ValueError:
        return uuid4()
    if parsed.version != 4:
        return uuid4()
    return parsed


class RequestIdMiddleware(AppMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Save a request id either from X-Request-ID header or newly generated"""
        request_id = _resolve_request_id(request.headers.get("X-Request-ID"))

        rid = str(request_id)
        request.state.request_id = rid
        rid_ctx = request_id_ctx.set(rid)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            request_id_ctx.reset(rid_ctx)


class LogMiddleware(AppMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time

        log_message = (
            "http_access method=%s path=%s status=%s duration_ms=%.1f"
            % (
                request.method,
                request.url.path,
                response.status_code,
                process_time * 1000,
            )
        )

        if request.url.path in _SKIP_OR_DEBUG:
            logger.debug(log_message)
        else:
            logger.info(log_message)

        return response
        