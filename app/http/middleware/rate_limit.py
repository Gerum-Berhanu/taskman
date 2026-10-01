"""HTTP middleware that enforces Redis-backed rate limits."""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import settings
from app.core.rate_limit_policies import select_middleware_fallback_policy
from app.http.rate_limit import evaluate_rate_limit, get_explicit_route_policy_name


_SKIP_OR_DEBUG = {"/health", "/favicon.ico"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Reject over-limit clients with 429; fail open if Redis errors."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if (
            not settings.rate_limit_enabled
            or request.url.path in _SKIP_OR_DEBUG
        ):
            return await call_next(request)

        explicit_route_policy = get_explicit_route_policy_name(request)
        if explicit_route_policy is not None:
            return await call_next(request)

        policy = select_middleware_fallback_policy(request.method, request.url.path)
        violation = await evaluate_rate_limit(request, policy)
        if violation is not None:
            return JSONResponse(
                {"detail": violation.detail},
                status_code=violation.status_code,
                headers=violation.headers,
            )
        return await call_next(request)
