"""Client session persistence DTOs."""

from datetime import datetime

from pydantic import UUID4, BaseModel, ConfigDict


class ClientSessionRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    user_id: UUID4
    active_token_id: UUID4 | None = None
    revoked_at: datetime | None = None
    created_at: datetime
    rotated_at: datetime | None = None
    expires_at: datetime


class ClientSessionCreateData(BaseModel):
    user_id: UUID4
