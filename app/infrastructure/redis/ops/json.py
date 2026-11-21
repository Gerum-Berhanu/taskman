"""JSON get/set helpers as a RedisClient mixin."""

from collections.abc import Mapping
import json
from typing import Any

from app.infrastructure.redis.ops.protocol import RedisConn


class JsonOpsMixin:
    async def get_json(self: RedisConn, key: str) -> dict[str, Any] | None:
        """Return a parsed JSON object, or None on miss."""
        raw = await self.get_client.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set_json(
        self: RedisConn,
        key: str,
        value: Mapping[str, Any],
        *,
        ttl_seconds: int,
    ) -> None:
        """Store JSON with a TTL (seconds)."""
        await self.get_client.set(key, json.dumps(value), ex=ttl_seconds)
