"""Client session persistence DTOs."""

from datetime import datetime
from uuid import uuid4

from pydantic import UUID4, BaseModel, ConfigDict, Field


class ClientSessionRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    user_id: UUID4
    active_token_id: UUID4 | None = None
    device_id: UUID4
    user_agent: str | None = None
    ip_address: str | None = None
    created_at: datetime
    rotated_at: datetime | None = None
    expires_at: datetime


class ClientSessionCreateData(BaseModel):
    user_id: UUID4
    device_id: UUID4 = Field(default_factory=uuid4)
    user_agent: str | None = Field(default=None, max_length=512)
    ip_address: str | None = Field(default=None, max_length=45)
