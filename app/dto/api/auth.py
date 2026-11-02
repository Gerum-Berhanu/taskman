from datetime import datetime
from pydantic import UUID4, BaseModel, Field

from app.core.config import settings
from app.dto.api.user import UserBase


class LoginCredentials(UserBase):
    password: str


class UserCreateResponse(UserBase):
    id: UUID4
    message: str = "User registered successfully"


class RegisterPendingResponse(BaseModel):
    """Returned after registration start; client must verify with OTP."""

    registration_id: UUID4
    message: str = "Check your email for a verification code"


class RegisterVerify(BaseModel):
    registration_id: UUID4
    otp: str = Field(
        min_length=settings.registration_otp_length,
        max_length=settings.registration_otp_length,
        pattern=rf"^\d{{{settings.registration_otp_length}}}$",
    )


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
