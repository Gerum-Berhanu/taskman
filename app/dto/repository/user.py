"""User persistence DTOs."""

from datetime import datetime

from pydantic import UUID4, BaseModel, ConfigDict, EmailStr


class UserRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    email: EmailStr
    hashed_password: str
    is_active: bool
    created_at: datetime


class UserCreateData(BaseModel):
    email: EmailStr
    hashed_password: str
