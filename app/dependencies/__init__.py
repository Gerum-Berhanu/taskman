"""FastAPI dependency injection call-site API."""

from app.dependencies.infra import SessionDep, UowDep, get_session, get_uow
from app.dependencies.rate_limit import (
    AuthLoginLimit,
    AuthLogoutLimit,
    AuthRefreshLimit,
    AuthRegisterLimit,
    DomainExportLimit,
    DomainReadLimit,
    DomainWriteLimit,
    RequireIPLimit,
    RequireUserLimit,
    SCOPES,
)
from app.dependencies.rbac import RequireRole, role_at_least
from app.dependencies.service import (
    AuthServiceDep,
    CurrentUserDep,
    TaskServiceDep,
    UserServiceDep,
    WorkspaceMemberServiceDep,
    WorkspaceServiceDep,
    get_current_user,
)

__all__ = [
    "AuthLoginLimit",
    "AuthLogoutLimit",
    "AuthRefreshLimit",
    "AuthRegisterLimit",
    "AuthServiceDep",
    "CurrentUserDep",
    "DomainExportLimit",
    "DomainReadLimit",
    "DomainWriteLimit",
    "RequireIPLimit",
    "RequireRole",
    "RequireUserLimit",
    "SCOPES",
    "SessionDep",
    "TaskServiceDep",
    "UowDep",
    "UserServiceDep",
    "WorkspaceMemberServiceDep",
    "WorkspaceServiceDep",
    "get_current_user",
    "get_session",
    "get_uow",
    "role_at_least",
]
