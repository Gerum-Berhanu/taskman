from typing import TypedDict
from uuid import UUID, uuid4

from app.core.config import settings
from app.infrastructure.redis.ops.hash import get_hash, hincrby, set_hash
from app.infrastructure.redis.ops.keys import delete_keys, key_exists


class PendingData(TypedDict):
    email: str
    hashed_password: str
    otp_hash: str
    attempts: int


def pending_key(registration_id: UUID) -> str:
    return f"register:pending:{registration_id}"


async def create_pending(*, email: str, hashed_password: str, otp_hash: str) -> UUID:
    """Let errors propagate to services to stay fail-closed"""
    opaque_id = uuid4()
    key = pending_key(opaque_id)
    value = {
        "email": email,
        "hashed_password": hashed_password,
        "otp_hash": otp_hash,
        "attempts": "0",
    }
    await set_hash(
        key,
        value,
        ttl_seconds=settings.registration_otp_ttl_seconds,
    )
    return opaque_id


async def get_pending(registration_id: UUID) -> PendingData | None:
    data = await get_hash(pending_key(registration_id))
    if data is None:
        return None
    return {
        "email": data["email"],
        "hashed_password": data["hashed_password"],
        "otp_hash": data["otp_hash"],
        "attempts": int(data["attempts"]),
    }


async def clear_pending(registration_id: UUID) -> None:
    await delete_keys(pending_key(registration_id))


async def incr_attempt(registration_id: UUID) -> int | None:
    """Bump attempts; return new count, or None if the ticket is gone."""
    key = pending_key(registration_id)
    if not await key_exists(key):
        return None
    return await hincrby(key, "attempts", 1)
