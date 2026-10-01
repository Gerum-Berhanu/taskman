"""HTTP middleware that enforces Redis-backed rate limits."""

import logging

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_429_TOO_MANY_REQUESTS

from app.core.config import settings
from app.infrastructure.redis.rate_limit_algorithms import hit_sliding_window_log


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
                {"detail": "Unknown client address"},
                status_code=HTTP_400_BAD_REQUEST,
            )

        ip = request.client.host
        policy, limit, window_seconds = _select_policy(request)

        try:
            result = await hit_sliding_window_log(
                policy=policy,
                identity=ip,
                limit=limit,
                window_seconds=window_seconds,
            )
        except Exception:  # broad Exception for now; later narrow to Redis/timeouts
            logger.exception(
                "rate_limit_backend_error policy=%s client=%s path=%s",
                policy,
                ip,
                request.url.path,
            )
            return await call_next(request)  # fail-open

        if not result.allowed:
            logger.warning(
                "rate_limit_exceeded policy=%s client=%s path=%s",
                policy,
                ip,
                request.url.path,
            )
            return JSONResponse(
                {"detail": "Rate limit exceeded"},
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(window_seconds)},
            )
        return await call_next(request)
