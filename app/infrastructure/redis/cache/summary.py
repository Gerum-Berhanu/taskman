"""Task summary cache: key shape and fail-open get/set/delete."""

import logging
from typing import Any
from uuid import UUID

from app.core.config import settings
from app.infrastructure.redis.errors import REDIS_DATA_ERRORS
from app.infrastructure.redis.ops.json import get_json, set_json
from app.infrastructure.redis.ops.keys import delete_keys
from app.observability.events import DomainLogEvent
from app.observability.log_event import log_event


logger = logging.getLogger(__name__)


def summary_key(workspace_id: UUID) -> str:
    return f"cache:ws:{workspace_id}:tasks:summary"


async def get_cached_summary(workspace_id: UUID) -> dict[str, Any] | None:
    """Return cached summary JSON, or None on miss / Redis failure."""
    key = summary_key(workspace_id)
    try:
        return await get_json(key)
    except REDIS_DATA_ERRORS:
        log_event(
            logger,
            logging.ERROR,
            DomainLogEvent.CACHE_BACKEND_ERROR,
            exc_info=True,
            op="get",
            key=key,
        )
        return None


async def set_cached_summary(workspace_id: UUID, payload: dict[str, Any]) -> None:
    """Store summary JSON; no-op on Redis failure."""
    key = summary_key(workspace_id)
    try:
        await set_json(
            key,
            payload,
            ttl_seconds=settings.task_summary_cache_ttl_seconds,
        )
    except REDIS_DATA_ERRORS:
        log_event(
            logger,
            logging.ERROR,
            DomainLogEvent.CACHE_BACKEND_ERROR,
            exc_info=True,
            op="set",
            key=key,
        )


async def invalidate_summary_cache(workspace_id: UUID) -> None:
    """Delete summary cache key; no-op on Redis failure.
    
    Early invalidate is fine (worst case: extra DB read if commit fails)."""
    
    key = summary_key(workspace_id)
    try:
        await delete_keys(key)
    except REDIS_DATA_ERRORS:
        log_event(
            logger,
            logging.ERROR,
            DomainLogEvent.CACHE_BACKEND_ERROR,
            exc_info=True,
            op="delete",
            key=key,
            workspace_id=workspace_id,
        )
