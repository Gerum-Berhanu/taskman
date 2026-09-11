from datetime import datetime
from enum import Enum
from pydantic import UUID4, BaseModel, Field


# Workspace schema

class WorkspaceBase(BaseModel):
    name: str = Field(max_length=255)


class WorkspaceCreate(WorkspaceBase):
    pass


class WorkspaceRead(WorkspaceBase):
    id: UUID4
    created_at: datetime


# Membership schema

class WorkspaceMemberRole(str, Enum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class MemberBaseSchema(BaseModel):
    user_id: UUID4
    role: WorkspaceMemberRole


class WorkspaceMemberCreate(MemberBaseSchema):
    pass


class WorkspaceMemberRead(MemberBaseSchema):
    workspace_id: UUID4
    joined_at: datetime
