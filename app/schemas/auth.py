from pydantic import UUID4, BaseModel

from app.schemas.base import UserBase


class LoginCredentials(UserBase):
    password: str


class UserCreateResponse(UserBase):
    id: UUID4
    message: str = "User registered successfully"


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
