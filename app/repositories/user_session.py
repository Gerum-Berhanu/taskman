"""User-session persistence (refresh-token rotation state)."""

from datetime import datetime, timedelta
from typing import TypedDict
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core import timeutils as tu
from app.core.config import settings
from app.core.security import hash_refresh_token
from app.models.refresh_token import UserSession


class UserSessionRecord(TypedDict):
    id: UUID
    user_id: UUID
    active_token_hash: str
    used_token_hashes: list[dict[str, str]]
    is_revoked: bool
    expires_at: datetime


def _to_record(user_session: UserSession) -> UserSessionRecord:
    return UserSessionRecord(
        id=user_session.id,
        user_id=user_session.user_id,
        active_token_hash=user_session.active_token_hash,
        used_token_hashes=user_session.used_token_hashes,
        is_revoked=user_session.is_revoked,
        expires_at=user_session.expires_at,
    )


class UserSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, user_id: UUID, token: str, session_id: UUID
    ) -> UserSessionRecord:
        user_session = UserSession(
            id=session_id,
            user_id=user_id,
            active_token_hash=hash_refresh_token(token),
        )
        self._session.add(user_session)
        await self._session.flush()
        await self._session.refresh(user_session)
        return _to_record(user_session)

    async def get(self, session_id: UUID) -> UserSessionRecord | None:
        user_session = await self._session.get(UserSession, session_id)
        if user_session is None:
            return None
        return _to_record(user_session)

    async def get_by_active_token_hash(self, token: str) -> UserSessionRecord | None:
        token_hash = hash_refresh_token(token)
        statement = select(UserSession).where(
            UserSession.active_token_hash == token_hash
        )
        result = await self._session.exec(statement)
        user_session = result.first()
        if user_session is None:
            return None
        return _to_record(user_session)

    async def rotate(
        self, session_id: UUID, *, new_token: str
    ) -> UserSessionRecord | None:
        """Move the current active hash into used history and install ``new_token``."""
        user_session = await self._session.get(UserSession, session_id)
        if user_session is None:
            return None

        used = list(user_session.used_token_hashes)
        used.append(
            {
                "hash": user_session.active_token_hash,
                "used_at": tu.utcnow().isoformat(),
            }
        )
        max_used = settings.refresh_token_used_history_size
        user_session.used_token_hashes = used[-max_used:]
        user_session.active_token_hash = hash_refresh_token(new_token)
        user_session.expires_at = tu.utcnow() + timedelta(
            minutes=settings.refresh_token_expire_minutes
        )

        self._session.add(user_session)
        await self._session.flush()
        await self._session.refresh(user_session)
        return _to_record(user_session)

    async def revoke(self, session_id: UUID) -> UserSessionRecord | None:
        user_session = await self._session.get(UserSession, session_id)
        if user_session is None:
            return None
        user_session.is_revoked = True
        self._session.add(user_session)
        await self._session.flush()
        await self._session.refresh(user_session)
        return _to_record(user_session)

    async def revoke_all_by_user(self, user_id: UUID) -> int:
        statement = select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.is_revoked == False,
        )
        result = await self._session.exec(statement)
        sessions = result.all()
        for session in sessions:
            session.is_revoked = True
            self._session.add(session)
        await self._session.flush()
        return len(sessions)
