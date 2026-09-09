from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import RefreshToken


class RefreshTokenRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_session_id: UUID
    token_hash: str


def _to_record(refresh_token: RefreshToken) -> RefreshTokenRecord:
    return RefreshTokenRecord.model_validate(refresh_token)


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
        return _to_record(refresh_token)

    async def get_by_token_hash(self, token_hash: str) -> RefreshTokenRecord | None:
        statement = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        refresh_token = await self._session.exec(statement)
        refresh_token = refresh_token.first()
        if refresh_token is None:
            return None
        return _to_record(refresh_token)
