"""Per-route Redis rate-limit dependencies and scope presets."""

import logging

from fastapi import Depends, Request

from app.core.config import settings
from app.core.exceptions import RateLimitExceededError, UnknownClientError
from app.deps import CurrentUserDep
from app.infrastructure.redis.lua import LuaScriptName
from app.infrastructure.redis.rate_limit_algorithms import HITTERS
from app.observability.events import HttpLogEvent
from app.observability.log_event import log_event


logger = logging.getLogger(__name__)


class _RequireLimit:
    def __init__(
        self,
        scope: str,
        *,
        limit: int,
        window_seconds: int,
        algorithm: LuaScriptName = "sliding_window_counter",
    ) -> None:
        self.scope = scope
        self.limit = limit
        self.window_seconds = window_seconds
        self.algorithm: LuaScriptName = algorithm

    async def _enforce_limit(self, identifier: str, log_kwargs: dict) -> None:
        """Shared execution pipeline for all rate limiters"""
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
        await self._enforce_limit(
            identifier=user_id,
            log_kwargs={"user_id": user_id},
        )


class RequireIPLimit(_RequireLimit):
    async def __call__(self, request: Request) -> None:
        if not request.client:
            raise UnknownClientError

        ip = request.client.host
        await self._enforce_limit(
            identifier=ip,
            log_kwargs={"ip": ip},
        )


AuthRegisterLimit = Depends(RequireIPLimit("auth.register", limit=3, window_seconds=60))
AuthLoginLimit = Depends(RequireIPLimit("auth.login", limit=5, window_seconds=60))
AuthRefreshLimit = Depends(RequireIPLimit("auth.refresh", limit=30, window_seconds=60))
AuthLogoutLimit = Depends(RequireIPLimit("auth.logout", limit=10, window_seconds=60))
DomainReadLimit = Depends(RequireUserLimit("domain.read", limit=100, window_seconds=60))
DomainWriteLimit = Depends(RequireUserLimit("domain.write", limit=30, window_seconds=60))
DomainExportLimit = Depends(RequireUserLimit("domain.export", limit=5, window_seconds=60))
