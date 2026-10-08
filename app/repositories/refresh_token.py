"""Refresh token persistence."""

from sqlmodel import select

from app.models import RefreshToken
from app.repositories.base import BaseRepository
from app.dto.repository import RefreshTokenCreateData, RefreshTokenRecord


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
        return self._to_record(refresh_token)
