"""ORM / SQLModel table models."""

from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel

from app.core.timeutils import utcnow

class User(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utcnow)

class Task(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(max_length=255)
    description: str | None = None
    status: str = Field(default="pending")
    due_date: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime | None = None