"""Pydantic request and response schemas."""

from enum import Enum
from pydantic import UUID4, BaseModel


class TaskCreate(BaseModel):
    title: str
    description: str | None = None


class TaskStatus(Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"


class TaskRead(BaseModel):
    id: UUID4
    title: str
    description: str | None
    status: TaskStatus