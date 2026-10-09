"""Async Redis client wrapper (rate limiting, task-summary cache, …)."""

import logging
from typing import get_args

from redis.asyncio import Redis
from redis.commands.core import AsyncScript

from app.core.config import settings
from app.infrastructure.redis.lua import LUA_SCRIPTS, LuaScriptName
from app.observability.events import InfraLogEvent


logger = logging.getLogger(__name__)


class RedisClient:
    """Process-wide Redis connection and registered Lua scripts."""

    def __init__(self) -> None:
        self._client: Redis | None = None
        self.scripts: dict[LuaScriptName, AsyncScript] = {}

    async def init_redis(self, redis_url: str = settings.redis_url) -> Redis:
        """Connect, ping, and register Lua scripts; raise if Redis is unreachable."""
        client = Redis.from_url(redis_url, decode_responses=True)
        try:
            await client.ping()
        except Exception:
            await client.aclose()
            self._client = None
            raise
        self._client = client
        self._register_scripts(LUA_SCRIPTS)
        return self._client

    async def init_redis_fail_open(
        self, redis_url: str = settings.redis_url
    ) -> Redis | None:
        """Like ``init_redis``, but log and return ``None`` on failure (app continues)."""
        try:
            return await self.init_redis(redis_url)
        except Exception:
            logger.exception(InfraLogEvent.REDIS_UNAVAILABLE_AT_STARTUP)
            return None


    async def close_redis(self) -> None:
        """Close the connection if one is open."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self.scripts = {}

    @property
    def get_redis_client(self) -> Redis:
        """Return the live client or raise if not initialized."""
        if self._client is None:
            raise RuntimeError("Redis is not initialized")
        return self._client

    def _register_scripts(self, lua_scripts: dict[LuaScriptName, str]) -> None:
        client = self.get_redis_client
        self.scripts = {
            name: client.register_script(lua_scripts[name])
            for name in get_args(LuaScriptName)
        }


redis_client = RedisClient()
