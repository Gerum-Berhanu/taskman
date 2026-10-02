"""Shared HTTP rate-limit helpers for middleware and dependencies."""

from dataclasses import dataclass
import logging

from fastapi import Request
from collections.abc import Iterator

from fastapi.routing import APIRoute
from starlette.routing import Match
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_429_TOO_MANY_REQUESTS

from app.core.rate_limit_policies import RateLimitIdentityMode, RateLimitPolicy
from app.infrastructure.redis.rate_limit_algorithms import hit_sliding_window_counter

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitViolation:
    """HTTP-ready rate-limit violation details."""

    status_code: int
    detail: str
    headers: dict[str, str] | None = None


async def evaluate_rate_limit(
    request: Request, policy: RateLimitPolicy
) -> RateLimitViolation | None:
    """Enforce one policy for one request (fail-open on backend errors)."""
    identity = _resolve_identity(request, policy)
    if identity is None:
        return RateLimitViolation(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Unknown client address",
        )

    try:
        result = await hit_sliding_window_counter(
            policy=policy.name,
            identity=identity,
            limit=policy.limit,
            window_seconds=policy.window_seconds,
        )
    except Exception:
        logger.exception(
            "rate_limit_backend_error policy=%s client=%s path=%s",
            policy.name,
            identity,
            request.url.path,
        )
        return None

    if result.allowed:
        return None

    logger.warning(
        "rate_limit_exceeded policy=%s client=%s path=%s",
        policy.name,
        identity,
        request.url.path,
    )
    return RateLimitViolation(
        status_code=HTTP_429_TOO_MANY_REQUESTS,
        detail="Rate limit exceeded",
        headers={"Retry-After": str(policy.window_seconds)},
    )


def get_explicit_route_policy_name(request: Request) -> str | None:
    """Return explicit route/group policy name, if one is declared."""
    for route in _iter_route_candidates(request.app.router.routes):
        match, _ = route.matches(request.scope)
        if match is not Match.FULL:
            continue
        for dependency in route.dependant.dependencies:
            policy_name = getattr(dependency.call, "__rate_limit_policy_name__", None)
            if policy_name is not None:
                return policy_name
    return None


def _resolve_identity(request: Request, policy: RateLimitPolicy) -> str | None:
    if policy.identity_mode == RateLimitIdentityMode.IP:
        return request.client.host if request.client else None
    raise ValueError(f"Unsupported rate-limit identity mode: {policy.identity_mode}")


def _iter_route_candidates(routes: list[object]) -> Iterator[APIRoute]:
    for route in routes:
        if isinstance(route, APIRoute):
            yield route
            continue
        candidates = getattr(route, "effective_candidates", None)
        if candidates is None:
            continue
        for candidate in candidates():
            if isinstance(candidate, APIRoute):
                yield candidate
                continue
            if hasattr(candidate, "dependant") and hasattr(candidate, "matches"):
                yield candidate
