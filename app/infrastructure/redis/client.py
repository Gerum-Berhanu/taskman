"""Async Redis client wrapper used for rate limiting."""

from redis.asyncio import Redis

from app.core.config import settings
from app.infrastructure.redis.lua import SLIDING_WINDOW_LOG


class RedisClient:
    """Process-wide Redis connection and registered Lua scripts."""

    def __init__(self):
        self._client: Redis | None = None  # redis client

    async def init_redis(self) -> Redis:
        """Connect, ping, and register Lua scripts; raise if Redis is unreachable."""
        client = Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            await client.ping()
        except Exception:
            await client.aclose()
            self._client = None
            raise
        self._client = client
        self._sliding_window = self._client.register_script(SLIDING_WINDOW_LOG)
        return self._client

    async def close_redis(self) -> None:
        """Close the connection if one is open."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def get_redis(self) -> Redis:
        """Return the live client or raise if not initialized."""
        if self._client is None:
            raise RuntimeError("Redis is not initialized")
        return self._client

    @property
    def sliding_window_script(self):
        """Registered sliding-window Lua script, or raise if Redis is down."""
        if self._client is None:
            raise RuntimeError("Redis is not initialized")
        return self._sliding_window


redis_client = RedisClient()
