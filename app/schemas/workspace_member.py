from datetime import datetime
from enum import Enum

from pydantic import UUID4, BaseModel


class WorkspaceMemberRole(str, Enum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class WorkspaceMemberCreate(BaseModel):
    user_id: UUID4
    role: WorkspaceMemberRole


class WorkspaceMemberRead(BaseModel):
    user_id: UUID4
    role: WorkspaceMemberRole
    workspace_id: UUID4
    joined_at: datetime
