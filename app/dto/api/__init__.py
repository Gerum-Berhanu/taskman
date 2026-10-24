"""HTTP-boundary DTOs (request/response contracts)."""

from app.dto.api.auth import (
    AccessTokenResponse,
    LoginCredentials,
    UserCreateResponse,
)
from app.dto.api.task import (
    TaskCreate,
    TaskRead,
    TaskStatus,
    TaskSummaryRead,
    TaskUpdate,
)
from app.dto.api.user import UserCreate, UserRead
from app.dto.api.workspace import WorkspaceCreate, WorkspaceRead
from app.dto.api.workspace_member import (
    WorkspaceMemberCreate,
    WorkspaceMemberRead,
    WorkspaceMemberRole,
)

__all__ = [
    "AccessTokenResponse",
    "LoginCredentials",
    "TaskCreate",
    "TaskRead",
    "TaskStatus",
    "TaskSummaryRead",
    "TaskUpdate",
    "UserCreate",
    "UserCreateResponse",
    "UserRead",
    "WorkspaceCreate",
    "WorkspaceMemberCreate",
    "WorkspaceMemberRead",
    "WorkspaceMemberRole",
    "WorkspaceRead",
]
