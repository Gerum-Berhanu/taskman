"""JSON get/set helpers on the shared async Redis client."""

from collections.abc import Mapping
import json
from typing import Any

from app.infrastructure.redis.client import redis_client


async def get_json(key: str) -> dict[str, Any] | None:
    """Return a parsed JSON object, or None on miss."""
    client = redis_client.get_redis_client
    raw = await client.get(key)
    if raw is None:
        return None
    return json.loads(raw)


async def set_json(
    key: str,
    value: Mapping[str, Any],
    *,
    ttl_seconds: int,
) -> None:
    """Store JSON with a TTL (seconds)."""
    client = redis_client.get_redis_client
    await client.set(key, json.dumps(value), ex=ttl_seconds)
