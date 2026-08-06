"""Pydantic request and response schemas."""

from datetime import datetime
from enum import Enum
from pydantic import UUID4, BaseModel, Field


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