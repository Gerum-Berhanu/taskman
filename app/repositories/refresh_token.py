from datetime import timedelta
from typing import Protocol
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core import timeutils as tu
from app.core.config import settings
from app.core.security import hash_refresh_token
from app.models.refresh_token import UserSession
from app.repositories.records import RefreshTokenUpdateData, UserSessionRecord


class RefreshTokenRepository(Protocol):
    async def create(
        self, *, user_id: UUID, token: str, session_id: UUID
    ) -> UserSessionRecord: ...

    async def get(self, family_id: UUID) -> UserSessionRecord | None: ...

    async def get_all_by_user(self, user_id: UUID) -> list[UserSessionRecord]: ...

    async def get_by_active_token_hash(self, token: str) -> UserSessionRecord | None: ...

    async def update(
        self, family_id: UUID, fields: RefreshTokenUpdateData
    ) -> UserSessionRecord | None: ...

    async def delete(self, family_id: UUID) -> bool: ...


def _to_user_session_record(user_session: UserSession) -> UserSessionRecord:
    return UserSessionRecord(
        id=user_session.id,
        user_id=user_session.user_id,
        active_token_hash=user_session.active_token_hash,
        used_token_hashes=user_session.used_token_hashes,
        is_revoked=user_session.is_revoked,
        expires_at=user_session.expires_at,
    )


class SqlRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, user_id: UUID, token: str, session_id: UUID
    ) -> UserSessionRecord:
        active_token_hash = hash_refresh_token(token)
        user_session = UserSession(
            id=session_id,
            user_id=user_id,
            active_token_hash=active_token_hash,
        )
        self._session.add(user_session)
        await self._session.flush()
        await self._session.refresh(user_session)
        return _to_user_session_record(user_session)

    async def get(self, family_id: UUID) -> UserSessionRecord | None:
        user_session = await self._session.get(UserSession, family_id)
        if user_session is None:
            return None
        return _to_user_session_record(user_session)

    async def get_all_by_user(self, user_id: UUID) -> list[UserSessionRecord]:
        statement = select(UserSession).where(UserSession.user_id == user_id)
        result = await self._session.exec(statement)
        user_sessions = result.all()
        return [_to_user_session_record(s) for s in user_sessions]

    async def get_by_active_token_hash(self, token: str) -> UserSessionRecord | None:
        token_hash = hash_refresh_token(token)
        statement = select(UserSession).where(UserSession.active_token_hash == token_hash)
        result = await self._session.exec(statement)
        user_session = result.first()
        if user_session is None:
            return None
        return _to_user_session_record(user_session)

    async def update(
        self, family_id: UUID, fields: RefreshTokenUpdateData
    ) -> UserSessionRecord | None:
        user_session = await self._session.get(UserSession, family_id)
        if user_session is None:
            return None
        if not fields:
            return _to_user_session_record(user_session)

        if "token" in fields:
            # fields["token"] is the freshly issued replacement, not the presented one.
            # Reuse detection (presented hash already in used_token_hashes) belongs in
            #   the auth service before calling update not here.
            old_hash = user_session.active_token_hash
            used = list(user_session.used_token_hashes)
            used.append({"hash": old_hash, "used_at": tu.utcnow().isoformat()})
            user_session.used_token_hashes = used
            user_session.active_token_hash = hash_refresh_token(fields["token"])
            user_session.expires_at = tu.utcnow() + timedelta(minutes=settings.refresh_token_expire_minutes)

        if "is_revoked" in fields:
            user_session.is_revoked = fields["is_revoked"]

        self._session.add(user_session)
        await self._session.flush()
        await self._session.refresh(user_session)
        return _to_user_session_record(user_session)

    async def delete(self, family_id: UUID) -> bool:
        user_session = await self._session.get(UserSession, family_id)
        if user_session is None:
            return False
        await self._session.delete(user_session)
        await self._session.flush()
        return True
