from uuid import UUID

from pydantic import UUID4, BaseModel, ConfigDict
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import RefreshToken
from app.repositories._persistence import add_flush_refresh, to_record


class RefreshTokenRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    client_session_id: UUID4
    token_hash: str


class RefreshTokenCreateData(BaseModel):
    client_session_id: UUID4
    token_hash: str


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, fields: RefreshTokenCreateData) -> RefreshTokenRecord:
        refresh_token = RefreshToken(**fields.model_dump())
        await add_flush_refresh(self._session, refresh_token)
        return to_record(RefreshTokenRecord, refresh_token)

    async def get_by_token_hash(self, token_hash: str) -> RefreshTokenRecord | None:
        statement = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        refresh_token = await self._session.exec(statement)
        refresh_token = refresh_token.first()
        if refresh_token is None:
            return None
        return to_record(RefreshTokenRecord, refresh_token)
