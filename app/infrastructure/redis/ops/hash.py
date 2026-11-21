"""Hash get/set/incr helpers as a RedisClient mixin."""

from collections.abc import Mapping

from app.infrastructure.redis.ops.protocol import RedisConn


class HashOpsMixin:
    async def set_hash(
        self: RedisConn,
        key: str,
        mapping: Mapping[str, str],
        *,
        ttl_seconds: int,
    ) -> None:
        """Store a hash and set TTL (seconds). Field values must already be strings."""
        client = self.get_client
        for field, value in mapping.items():
            await client.hset(key, field, value)
        await client.expire(key, ttl_seconds)

    async def get_hash(self: RedisConn, key: str) -> dict[str, str] | None:
        """Return all hash fields, or None when the key is missing/empty."""
        data = await self.get_client.hgetall(key)
        if not data:
            return None
        return {str(k): str(v) for k, v in data.items()}

    async def hincrby(
        self: RedisConn, key: str, field: str, amount: int = 1
    ) -> int:
        """Atomically increment a hash integer field; returns the new value."""
        return int(await self.get_client.hincrby(key, field, amount))
