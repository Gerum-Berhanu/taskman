"""Pydantic request and response schemas for users and auth."""

from datetime import datetime

from pydantic import UUID4, BaseModel, EmailStr, Field


class _UserCredentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserCreate(_UserCredentials):
    pass


class UserAuthenticate(_UserCredentials):
    pass


class UserCreateResponse(BaseModel):
    id: UUID4
    email: EmailStr
    message: str = "User registered successfully"


class UserRead(BaseModel):
    id: UUID4
    email: EmailStr
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str
