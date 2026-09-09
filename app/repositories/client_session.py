from datetime import datetime, timedelta
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.timeutils import utcnow
from app.models import ClientSession


class ClientSessionRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    active_token_id: UUID | None
    revoked_at: datetime | None
    created_at: datetime
    rotated_at: datetime | None
    expires_at: datetime


def _to_record(client_session: ClientSession) -> ClientSessionRecord:
    return ClientSessionRecord.model_validate(client_session)


class ClientSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user_id: UUID) -> ClientSessionRecord:
        client_session = ClientSession(user_id=user_id)
        self._session.add(client_session)
        await self._session.flush()
        await self._session.refresh(client_session)
        return _to_record(client_session)

    async def get_by_id(self, client_id: UUID) -> ClientSessionRecord | None:
        client_session = await self._session.get(ClientSession, client_id)
        if client_session is None:
            return None
        return _to_record(client_session)

    async def set_active_token_id(self, *, client_id: UUID,  token_id: UUID, is_rotation: bool = False) -> ClientSessionRecord | None:
        client_session = await self._session.get(ClientSession, client_id)
        if client_session is None:
            return None

        client_session.active_token_id = token_id
        if is_rotation:
            client_session.rotated_at = utcnow()
            client_session.expires_at = (
                utcnow() + timedelta(minutes=settings.refresh_token_expire_minutes)
            )

        self._session.add(client_session)
        await self._session.flush()
        await self._session.refresh(client_session)
        return _to_record(client_session)
    
    async def revoke(self, client_id: UUID) -> bool:
        client_session = await self._session.get(ClientSession, client_id)
        if not client_session:
            return False
        client_session.active_token_id = None
        client_session.revoked_at = utcnow()
        self._session.add(client_session)
        await self._session.flush()
        await self._session.refresh(client_session)
        return True
    