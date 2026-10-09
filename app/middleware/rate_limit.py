"""HTTP middleware that enforces Redis-backed rate limits."""

import logging

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_429_TOO_MANY_REQUESTS

from app.core.config import settings
from app.infrastructure.redis.rate_limit_algorithms import hit_sliding_window_counter
from app.observability.events import HttpLogEvent
from app.observability.log_event import log_event


_SKIP_OR_DEBUG = {"/health", "/favicon.ico"}
_AUTH_PATH_PREFIX = "/auth"

logger = logging.getLogger(__name__)


def _select_policy(request: Request) -> tuple[str, int, int]:
    """Pick (policy, limit, window_seconds) for this request."""
    if request.method == "POST" and request.url.path.startswith(_AUTH_PATH_PREFIX):
        return ("auth", settings.rate_limit_auth_requests, settings.rate_limit_auth_window_seconds)
    return ("default", settings.rate_limit_requests, settings.rate_limit_window_seconds)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Reject over-limit clients with 429; fail open if Redis errors."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if (
            not settings.rate_limit_enabled
            or request.url.path in _SKIP_OR_DEBUG
        ):
            return await call_next(request)

        if not request.client:
            return JSONResponse(
                status_code=HTTP_400_BAD_REQUEST,
                content={"detail": "Unknown client address"},
            )

        ip = request.client.host
        policy, limit, window_seconds = _select_policy(request)

        try:
            result = await hit_sliding_window_counter(
                policy=policy,
                identity=ip,
                limit=limit,
                window_seconds=window_seconds,
            )
        except Exception:  # broad Exception for now; later narrow to Redis/timeouts
            log_event(
                logger,
                logging.ERROR,
                HttpLogEvent.RATE_LIMIT_BACKEND_ERROR,
                exc_info=True,
                ip=ip,
                policy=policy,
            )
            return await call_next(request)  # fail-open

        if not result.allowed:
            log_event(
                logger,
                logging.WARNING,
                HttpLogEvent.RATE_LIMIT_EXCEEDED,
                ip=ip,
                policy=policy,
            )
            return JSONResponse(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(window_seconds)},
            )
        return await call_next(request)
