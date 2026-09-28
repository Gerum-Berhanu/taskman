from redis.asyncio import Redis
from app.core.config import settings
from app.core.lua_scripts import SLIDING_WINDOW


class RedisClient:
    def __init__(self):
        self._client: Redis | None = None # redis client

    async def init_redis(self) -> Redis:
        self._client = Redis.from_url(settings.redis_url, decode_responses=True)
        await self._client.ping()
        self._sliding_window = self._client.register_script(SLIDING_WINDOW)
        return self._client

    async def close_redis(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def get_redis(self) -> Redis:
        if self._client is None:
            raise RuntimeError("Redis is not initialized")
        return self._client

    @property
    def sliding_window_script(self):
        if self._client is None:
            raise RuntimeError("Redis is not initialized")
        return self._sliding_window


redis_client = RedisClient()
        