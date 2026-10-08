"""Task persistence DTOs."""

from datetime import datetime

from pydantic import UUID4, BaseModel, ConfigDict


class TaskRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    title: str
    description: str | None = None
    status: str
    due_date: datetime | None = None
    workspace_id: UUID4
    assigned_user_id: UUID4 | None = None
    created_at: datetime
    updated_at: datetime | None = None


class TaskCreateData(BaseModel):
    title: str
    description: str | None = None
    due_date: datetime | None = None
    workspace_id: UUID4
    assigned_user_id: UUID4 | None = None


class TaskUpdateData(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    due_date: datetime | None = None
    assigned_user_id: UUID4 | None = None
