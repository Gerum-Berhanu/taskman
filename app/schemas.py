"""Pydantic request and response schemas."""

from enum import Enum
from pydantic import UUID4, BaseModel, Field


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None


class TaskStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"


class TaskRead(BaseModel):
    id: UUID4
    title: str
    description: str | None
    status: TaskStatus


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None