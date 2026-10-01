"""Centralized named rate-limit policies."""

from dataclasses import dataclass
from enum import StrEnum

from app.core.config import settings


class RateLimitIdentityMode(StrEnum):
    """Identity mode for policy evaluation (future extension point)."""

    IP = "ip"


@dataclass(frozen=True)
class RateLimitPolicy:
    """Named policy backed by configurable limits."""

    name: str
    limit: int
    window_seconds: int
    identity_mode: RateLimitIdentityMode = RateLimitIdentityMode.IP


DEFAULT_POLICY = "default"
AUTH_POLICY = "auth"
TASK_READS_POLICY = "task_reads"
TASK_WRITES_POLICY = "task_writes"


def get_rate_limit_policies() -> dict[str, RateLimitPolicy]:
    """Build the policy registry from current settings."""
    return {
        DEFAULT_POLICY: RateLimitPolicy(
            name=DEFAULT_POLICY,
            limit=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        ),
        AUTH_POLICY: RateLimitPolicy(
            name=AUTH_POLICY,
            limit=settings.rate_limit_auth_requests,
            window_seconds=settings.rate_limit_auth_window_seconds,
        ),
        TASK_READS_POLICY: RateLimitPolicy(
            name=TASK_READS_POLICY,
            limit=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        ),
        TASK_WRITES_POLICY: RateLimitPolicy(
            name=TASK_WRITES_POLICY,
            limit=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        ),
    }


def get_rate_limit_policy(policy_name: str) -> RateLimitPolicy:
    """Fetch a named policy."""
    try:
        return get_rate_limit_policies()[policy_name]
    except KeyError as exc:
        raise ValueError(f"Unknown rate-limit policy: {policy_name}") from exc


def select_middleware_fallback_policy(method: str, path: str) -> RateLimitPolicy:
    """Select middleware fallback policy (preserves existing auth/default behavior)."""
    if method == "POST" and path.startswith("/auth"):
        return get_rate_limit_policy(AUTH_POLICY)
    return get_rate_limit_policy(DEFAULT_POLICY)
