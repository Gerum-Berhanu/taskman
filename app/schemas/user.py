"""Pydantic request and response schemas for users."""

from datetime import datetime

from pydantic import UUID4, Field

from app.schemas.base import UserBase


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserRead(UserBase):
    id: UUID4
    is_active: bool
    created_at: datetime
