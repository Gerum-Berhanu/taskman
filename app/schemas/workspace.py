from datetime import datetime

from pydantic import UUID4, BaseModel, Field


class WorkspaceBase(BaseModel):
    name: str = Field(max_length=255)


class WorkspaceCreate(WorkspaceBase):
    pass


class WorkspaceRead(WorkspaceBase):
    id: UUID4
    created_at: datetime
