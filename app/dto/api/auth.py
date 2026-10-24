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
