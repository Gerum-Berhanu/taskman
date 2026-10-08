"""Workspace membership persistence DTOs."""

from datetime import datetime

from pydantic import UUID4, BaseModel, ConfigDict


class WorkspaceMemberRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workspace_id: UUID4
    user_id: UUID4
    role: str
    joined_at: datetime


class WorkspaceMemberCreateData(BaseModel):
    workspace_id: UUID4
    user_id: UUID4
    role: str
