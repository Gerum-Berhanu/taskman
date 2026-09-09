from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import RefreshToken


class RefreshTokenRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_session_id: UUID
    token_hash: str


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, client_session_id: UUID, token_hash: str) -> RefreshTokenRecord:
        refresh_token = RefreshToken(
            client_session_id=client_session_id,
            token_hash=token_hash
        )
        self._session.add(refresh_token)
        await self._session.flush()
        await self._session.refresh(refresh_token)
        return RefreshTokenRecord.model_validate(refresh_token)
