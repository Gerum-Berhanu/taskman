"""Client session persistence."""

from datetime import datetime, timedelta
from uuid import UUID

from pydantic import UUID4, BaseModel, ConfigDict
from sqlmodel import select

from app.core.config import settings
from app.core.timeutils import utcnow
from app.models import ClientSession
from app.repositories.base import BaseRepository


class ClientSessionRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    user_id: UUID4
    active_token_id: UUID4 | None
    revoked_at: datetime | None
    created_at: datetime
    rotated_at: datetime | None
    expires_at: datetime


class ClientSessionRepository(BaseRepository):
    async def create(self, user_id: UUID) -> ClientSessionRecord:
        """Create a new client session for the user."""
        client_session = ClientSession(user_id=user_id)
        await self.add_flush_refresh(client_session)
        return self.to_record(ClientSessionRecord, client_session)

    async def get_by_id(self, client_id: UUID) -> ClientSessionRecord | None:
        """Fetch a client session by id, or None."""
        client_session = await self._session.get(ClientSession, client_id)
        if client_session is None:
            return None
        return self.to_record(ClientSessionRecord, client_session)

    async def set_active_token_id(
        self,
        *,
        client_id: UUID,
        token_id: UUID,
        is_rotation: bool = False,
    ) -> ClientSessionRecord | None:
        """Point the session at a refresh token; optionally bump rotation/expiry."""
        client_session = await self._session.get(ClientSession, client_id)
        if client_session is None:
            return None

        client_session.active_token_id = token_id
        if is_rotation:
            client_session.rotated_at = utcnow()
            client_session.expires_at = utcnow() + timedelta(
                minutes=settings.refresh_token_expire_minutes
            )

        await self.flush_refresh(client_session)
        return self.to_record(ClientSessionRecord, client_session)

    async def revoke(self, client_id: UUID) -> bool:
        """Revoke one session; False if it did not exist."""
        client_session = await self._session.get(ClientSession, client_id)
        if client_session is None:
            return False
        client_session.active_token_id = None
        client_session.revoked_at = utcnow()
        await self.flush_refresh(client_session)
        return True

    async def revoke_all_user_sessions(self, user_id: UUID) -> int:
        """Revoke every session for a user; return how many were updated."""
        statement = select(ClientSession).where(ClientSession.user_id == user_id)
        result = await self._session.exec(statement)
        client_sessions = result.all()

        for session in client_sessions:
            session.active_token_id = None
            session.revoked_at = utcnow()

        if client_sessions:
            await self._session.flush(client_sessions)

        return len(client_sessions)
