"""HTTP middleware that enforces Redis-backed rate limits."""

import logging

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_429_TOO_MANY_REQUESTS

from app.core.config import settings
from app.core.rate_limit_policies import select_middleware_fallback_policy
from app.infrastructure.redis.rate_limit_algorithms import hit_sliding_window_counter


_SKIP_OR_DEBUG = {"/health", "/favicon.ico"}

logger = logging.getLogger(__name__)


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
        policy = select_middleware_fallback_policy(request.method, request.url.path)

        try:
            result = await hit_sliding_window_counter(
                policy=policy.name,
                identity=ip,
                limit=policy.limit,
                window_seconds=policy.window_seconds,
            )
        except Exception:  # broad Exception for now; later narrow to Redis/timeouts
            logger.exception(
                "rate_limit_backend_error policy=%s client=%s path=%s",
                policy.name,
                ip,
                request.url.path,
            )
            return await call_next(request)  # fail-open

        if not result.allowed:
            logger.warning(
                "rate_limit_exceeded policy=%s client=%s path=%s",
                policy.name,
                ip,
                request.url.path,
            )
            return JSONResponse(
                {"detail": "Rate limit exceeded"},
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(policy.window_seconds)},
            )
        return await call_next(request)
