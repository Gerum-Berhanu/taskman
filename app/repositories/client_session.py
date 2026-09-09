from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import ClientSession


class ClientSessionRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    active_token_id: UUID | None
    is_revoked: bool
    created_at: datetime
    rotated_at: datetime | None
    expires_at: datetime


class ClientSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user_id: UUID) -> ClientSessionRecord:
        client_session = ClientSession(user_id=user_id)
        self._session.add(client_session)
        await self._session.flush()
        await self._session.refresh(client_session)
        return ClientSessionRecord.model_validate(client_session)
