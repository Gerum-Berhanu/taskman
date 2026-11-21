"""Async Redis client wrapper (rate limiting, task-summary cache, ...)."""

from dataclasses import dataclass, fields
import logging
from typing import get_args

from redis.asyncio import Redis
from redis.commands.core import AsyncScript
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError

from app.core.config import settings
from app.infrastructure.redis.lua_loader import LUA_SCRIPTS, LuaScriptName
from app.infrastructure.redis.ops import RedisOps
from app.observability.events import InfraLogEvent
from app.observability.log_event import log_event


logger = logging.getLogger(__name__)

# Ping / connect failures at startup (redis-py plus socket-level errors).
_INIT_ERRORS = (RedisError, TimeoutError, OSError)


class RedisClient(RedisOps):
    """Process-wide Redis connection, ops helpers, and optional Lua scripts."""

    def __init__(self, redis_url: str, role: str, with_scripts: bool = False) -> None:
        self._client: Redis | None = None
        self.redis_url: str = redis_url
        self.role: str = role
        self.with_scripts: bool = with_scripts
        self.scripts: dict[LuaScriptName, AsyncScript] = {}

    async def init(self) -> Redis:
        """Connect, ping, and optionally register Lua scripts; raise if Redis is unreachable."""
        client = Redis.from_url(self.redis_url, decode_responses=True)
        try:
            await client.ping()
        except _INIT_ERRORS:
            await client.aclose()
            self._client = None
            raise
        self._client = client
        if self.with_scripts:
            self._register_scripts(LUA_SCRIPTS)
        return self._client

    async def init_fail_open(self) -> Redis | None:
        """Like init, but log and return None on failure (app continues)."""
        try:
            return await self.init()
        except _INIT_ERRORS:
            log_event(
                logger,
                logging.ERROR,
                InfraLogEvent.REDIS_UNAVAILABLE_AT_STARTUP,
                exc_info=True,
                role=self.role,
            )
            return None

    async def close(self) -> None:
        """Close the connection if one is open."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self.scripts = {}

    @property
    def get_client(self) -> Redis:
        """Return the live client or raise if not initialized."""
        if self._client is None:
            raise RedisConnectionError("Redis is not initialized")
        return self._client

    def _register_scripts(self, lua_scripts: dict[LuaScriptName, str]) -> None:
        client = self.get_client
        self.scripts = {
            name: client.register_script(lua_scripts[name])
            for name in get_args(LuaScriptName)
        }


@dataclass(frozen=True, slots=True)
class RedisClients:
    cache: RedisClient
    rate_limit: RedisClient
    registration: RedisClient

    def __iter__(self):
        for f in fields(self):
            yield getattr(self, f.name)

    async def init_all_fail_open(self) -> None:
        for client in self:
            await client.init_fail_open()

    async def close_all(self) -> None:
        for client in self:
            await client.close()


redis_clients = RedisClients(
    cache=RedisClient(settings.redis_cache_url, role="cache"),
    rate_limit=RedisClient(settings.redis_rate_limit_url, role="rate_limit", with_scripts=True),
    registration=RedisClient(settings.redis_registration_url, role="registration"),
)
# short alias
rc = redis_clients
