from datetime import datetime
from sqlmodel import Field

from app.models.base import BaseTable


class Task(BaseTable, table=True):
    __tablename__: str = "tasks"

    title: str = Field(max_length=255)
    description: str | None = None
    status: str = Field(default="pending")
    due_date: datetime | None = None
    updated_at: datetime | None = None