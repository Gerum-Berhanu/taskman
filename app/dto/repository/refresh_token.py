"""Refresh token persistence DTOs."""

from pydantic import UUID4, BaseModel, ConfigDict


class RefreshTokenRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    client_session_id: UUID4
    token_hash: str


class RefreshTokenCreateData(BaseModel):
    client_session_id: UUID4
    token_hash: str
