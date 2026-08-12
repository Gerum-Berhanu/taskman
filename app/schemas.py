"""Pydantic request and response schemas."""

from datetime import datetime
from enum import Enum
from pydantic import UUID4, BaseModel, EmailStr, Field


class TaskStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    due_date: datetime | None = None


class TaskRead(BaseModel):
    id: UUID4
    title: str
    description: str | None
    status: TaskStatus
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime | None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    due_date: datetime | None = None


# ---


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserCreateResponse(BaseModel):
    id: UUID4
    email: EmailStr
    message: str = "User registered successfully"


class UserAuthenticate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserRead(BaseModel):
    id: UUID4
    email: EmailStr
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str