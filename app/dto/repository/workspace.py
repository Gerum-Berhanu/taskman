"""Workspace persistence DTOs."""

from datetime import datetime

from pydantic import UUID4, BaseModel, ConfigDict


class WorkspaceRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    name: str
    created_at: datetime


class WorkspaceCreateData(BaseModel):
    name: str
