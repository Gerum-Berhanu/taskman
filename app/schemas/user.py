"""Pydantic request and response schemas for users."""

from datetime import datetime

from pydantic import UUID4, BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserRead(UserBase):
    id: UUID4
    is_active: bool
    created_at: datetime
