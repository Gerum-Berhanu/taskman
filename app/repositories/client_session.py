"""Client session persistence."""

from datetime import datetime, timedelta
from uuid import UUID

from pydantic import UUID4, BaseModel, ConfigDict
from sqlmodel import select

from app.core.config import settings
from app.core.timeutils import utcnow
from app.models import ClientSession
from app.repositories._persistence import add_flush_refresh, to_record
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
        client_session = ClientSession(user_id=user_id)
        await add_flush_refresh(self._session, client_session)
        return to_record(ClientSessionRecord, client_session)

    async def get_by_id(self, client_id: UUID) -> ClientSessionRecord | None:
        client_session = await self._session.get(ClientSession, client_id)
        if client_session is None:
            return None
        return to_record(ClientSessionRecord, client_session)

    async def set_active_token_id(
        self,
        *,
        client_id: UUID,
        token_id: UUID,
        is_rotation: bool = False,
    ) -> ClientSessionRecord | None:
        client_session = await self._session.get(ClientSession, client_id)
        if client_session is None:
            return None

        client_session.active_token_id = token_id
        if is_rotation:
            client_session.rotated_at = utcnow()
            client_session.expires_at = utcnow() + timedelta(
                minutes=settings.refresh_token_expire_minutes
            )

        await add_flush_refresh(self._session, client_session)
        return to_record(ClientSessionRecord, client_session)

    async def revoke(self, client_id: UUID) -> bool:
        client_session = await self._session.get(ClientSession, client_id)
        if client_session is None:
            return False
        client_session.active_token_id = None
        client_session.revoked_at = utcnow()
        await add_flush_refresh(self._session, client_session)
        return True

    async def revoke_all_user_sessions(self, user_id: UUID) -> int:
        statement = select(ClientSession).where(ClientSession.user_id == user_id)
        result = await self._session.exec(statement)
        client_sessions = result.all()

        for session in client_sessions:
            session.active_token_id = None
            session.revoked_at = utcnow()
        
        if client_sessions:
            await self._session.flush(client_sessions)

        return len(client_sessions)
