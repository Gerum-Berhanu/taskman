"""Refresh token persistence."""

from pydantic import UUID4, BaseModel, ConfigDict
from sqlmodel import select

from app.models import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    client_session_id: UUID4
    token_hash: str


class RefreshTokenCreateData(BaseModel):
    client_session_id: UUID4
    token_hash: str


class RefreshTokenRepository(
    BaseRepository[RefreshToken, RefreshTokenRecord, RefreshTokenCreateData]
):
    model = RefreshToken
    record = RefreshTokenRecord

    async def get_by_token_hash(self, token_hash: str) -> RefreshTokenRecord | None:
        """Look up a refresh token by its stored hash, or None."""
        statement = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self._session.exec(statement)
        refresh_token = result.first()
        if refresh_token is None:
            return None
        return self.to_record(refresh_token)
