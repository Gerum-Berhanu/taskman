import logging
import time
from uuid import UUID, uuid4
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from app.core.config import settings
from app.core.rate_limit import hit_sliding_window
from app.core.request_context import request_id_ctx


_SKIP_OR_DEBUG = {"/health", "/favicon.ico"}
_AUTH_PATH_PREFIX = "/auth"

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


def _select_policy(request: Request) -> tuple[str, int, int]:
    """Returns (policy, limit, window_seconds)"""
    if request.method == "POST" and request.url.path.startswith(_AUTH_PATH_PREFIX):
        return ("auth", settings.rate_limit_auth_requests, settings.rate_limit_auth_window_seconds)
    return ("default", settings.rate_limit_requests, settings.rate_limit_window_seconds)


class RateLimitMiddleware(AppMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if (
            not settings.rate_limit_enabled
            or request.url.path in _SKIP_OR_DEBUG
        ):
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        policy, limit, window_seconds = _select_policy(request)
        
        result = await hit_sliding_window(
            policy=policy,
            identity=ip,
            limit=limit,
            window_seconds=window_seconds,
        )

        if not result.allowed:
            return JSONResponse(
                {"detail": "Rate limit exceeded"}, 
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(window_seconds)},
            )
        return await call_next(request)


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
        