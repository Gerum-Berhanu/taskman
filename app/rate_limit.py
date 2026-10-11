"""Per-route Redis rate-limit dependencies and scope presets."""

from dataclasses import dataclass
import logging
from typing import Any, Literal

from fastapi import Depends, Request

from app.core.config import settings
from app.core.exceptions import RateLimitExceededError, UnknownClientError
from app.deps import CurrentUserDep
from app.infrastructure.redis.lua import LuaScriptName
from app.infrastructure.redis.rate_limit_algorithms import HITTERS
from app.observability.events import HttpLogEvent
from app.observability.log_event import log_event


logger = logging.getLogger(__name__)

IdentityMode = Literal["ip", "user"]


@dataclass(frozen=True, slots=True)
class ScopeSpec:
    """Budget for one named rate-limit scope."""

    identity: IdentityMode
    limit: int
    window_seconds: int = 60
    algorithm: LuaScriptName = "sliding_window_counter"


# Single place to tune budgets. Same scope name => shared Redis counter.
SCOPES: dict[str, ScopeSpec] = {
    "auth.register": ScopeSpec(identity="ip", limit=3),
    "auth.login": ScopeSpec(identity="ip", limit=5),
    "auth.refresh": ScopeSpec(identity="ip", limit=30),
    "auth.logout": ScopeSpec(identity="ip", limit=10),
    "domain.read": ScopeSpec(identity="user", limit=100),
    "domain.write": ScopeSpec(identity="user", limit=30),
    "domain.export": ScopeSpec(identity="user", limit=5),
}


class _RequireLimit:
    """Shared Redis hit pipeline; constructed from a SCOPES entry."""

    def __init__(self, scope: str) -> None:
        spec = SCOPES[scope]
        self.scope = scope
        self.limit = spec.limit
        self.window_seconds = spec.window_seconds
        self.algorithm: LuaScriptName = spec.algorithm

    async def _enforce_limit(self, identifier: str, log_kwargs: dict) -> None:
        if not settings.rate_limit_enabled:
            return

        hit = HITTERS[self.algorithm]
        try:
            result = await hit(
                scope=self.scope,
                identity=identifier,
                limit=self.limit,
                window_seconds=self.window_seconds,
            )
        except Exception:
            log_event(
                logger,
                logging.ERROR,
                HttpLogEvent.RATE_LIMIT_BACKEND_ERROR,
                exc_info=True,
                scope=self.scope,
                **log_kwargs,
            )
            return  # fail-open

        if not result.allowed:
            log_event(
                logger,
                logging.WARNING,
                HttpLogEvent.RATE_LIMIT_EXCEEDED,
                scope=self.scope,
                **log_kwargs,
            )
            raise RateLimitExceededError(self.window_seconds)


class RequireUserLimit(_RequireLimit):
    async def __call__(self, current_user: CurrentUserDep) -> None:
        user_id = str(current_user.id)
        await self._enforce_limit(user_id, {"user_id": user_id})


class RequireIPLimit(_RequireLimit):
    async def __call__(self, request: Request) -> None:
        if not request.client:
            raise UnknownClientError
        ip = request.client.host
        await self._enforce_limit(ip, {"ip": ip})


def _limit_dep(scope: str) -> Any:
    """Build Depends(...) from SCOPES; picks IP vs user by identity mode."""
    spec = SCOPES[scope]
    cls = RequireIPLimit if spec.identity == "ip" else RequireUserLimit
    return Depends(cls(scope))


AuthRegisterLimit = _limit_dep("auth.register")
AuthLoginLimit = _limit_dep("auth.login")
AuthRefreshLimit = _limit_dep("auth.refresh")
AuthLogoutLimit = _limit_dep("auth.logout")
DomainReadLimit = _limit_dep("domain.read")
DomainWriteLimit = _limit_dep("domain.write")
DomainExportLimit = _limit_dep("domain.export")
