from datetime import datetime
from pydantic import UUID4, BaseModel

from app.dto.api.user import UserBase


class LoginCredentials(UserBase):
    password: str


class UserCreateResponse(UserBase):
    id: UUID4
    message: str = "User registered successfully"


class AccessTokenResponse(BaseModel):
    """Access token in the JSON body; refresh is delivered via HttpOnly cookie."""

    access_token: str
    token_type: str = "bearer"


class ClientSessionRead(BaseModel):
    id: UUID4
    device_id: UUID4
    user_agent: str | None
    ip_address: str | None
    created_at: datetime
    rotated_at: datetime | None
    expires_at: datetime
    is_current: bool = False
