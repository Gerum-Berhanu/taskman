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


class RequestIdMiddleware(AppMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Save a request id either from X-Request-ID header or newly generated"""
        presented_id = request.headers.get("X-Request-ID")
        if not presented_id:
            request_id = uuid4()
        else:
            try:
                request_id = UUID(presented_id, version=4)
            except ValueError:
                request_id = uuid4()

        rid = str(request_id)
        request.state.request_id = rid
        token = request_id_ctx.set(rid)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            request_id_ctx.reset(token)


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
        