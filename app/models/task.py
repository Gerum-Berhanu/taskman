from datetime import datetime
from uuid import UUID
from sqlmodel import Field

from app.models.base import BaseTable


class Task(BaseTable, table=True):
    __tablename__: str = "tasks"

    title: str = Field(max_length=255)
    description: str | None = None
    status: str = Field(default="pending")
    due_date: datetime | None = None
    workspace_id: UUID = Field(foreign_key="workspaces.id", ondelete="CASCADE", index=True)
    assigned_user_id: UUID | None = Field(default=None, foreign_key="users.id", ondelete="SET NULL")
    updated_at: datetime | None = None