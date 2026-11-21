"""Key-level helpers as a RedisClient mixin."""

from app.infrastructure.redis.ops.protocol import RedisConn


class KeysOpsMixin:
    async def key_exists(self: RedisConn, key: str) -> bool:
        """Return True when the key exists."""
        return bool(await self.get_client.exists(key))

    async def delete_keys(self: RedisConn, *keys: str) -> None:
        """Delete one or more keys (no-op if empty)."""
        if not keys:
            return
        await self.get_client.delete(*keys)
