"""Async Redis client wrapper used for rate limiting."""

from redis.asyncio import Redis
from redis.commands.core import AsyncScript

from app.core.config import settings


class RedisClient:
    """Process-wide Redis connection and registered Lua scripts."""

    def __init__(self):
        self._client: Redis | None = None  # redis client

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
        return self._client

    async def close_redis(self) -> None:
        """Close the connection if one is open."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            
    @property
    def get_redis(self) -> Redis:
        """Return the live client or raise if not initialized."""
        if self._client is None:
            raise RuntimeError("Redis is not initialized")
        return self._client

    def register_script(self, script_text: str) -> AsyncScript:
        client = self.get_redis
        self._script = client.register_script(script_text)
        return self._script


redis_client = RedisClient()
