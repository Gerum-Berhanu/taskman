"""JSON cache helpers backed by the shared async Redis client."""

import json
from typing import Any
from uuid import UUID

from app.core.config import settings
from app.infrastructure.redis.client import redis_client


def task_summary_key(workspace_id: UUID) -> str:
    return f"cache:ws:{workspace_id}:tasks:summary"


async def get_json(key: str) -> dict[str, Any] | None:
    """Return a parsed JSON object, or None on miss."""
    client = redis_client.get_redis_client
    raw = await client.get(key)
    if raw is None:
        return None
    return json.loads(raw)


async def set_json(
    key: str,
    value: dict[str, Any],
    *,
    ttl_seconds: int = settings.task_summary_cache_ttl_seconds,
) -> None:
    """Store JSON with a TTL (seconds)."""
    client = redis_client.get_redis_client
    await client.set(key, json.dumps(value), ex=ttl_seconds)


async def delete_keys(*keys: str) -> None:
    """Delete one or more cache keys (no-op if empty)."""
    if not keys:
        return
    client = redis_client.get_redis_client
    await client.delete(*keys)