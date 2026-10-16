"""Dependency injection wiring for services and auth."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

from app.core.request_context import current_user_id_ctx
from app.dependencies.infra import UowDep
from app.dto.api.user import UserRead
from app.services.auth import AuthService
from app.services.task import TaskService
from app.services.user import UserService
from app.services.workspace import WorkspaceService
from app.services.workspace_member import WorkspaceMemberService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_task_service(uow: UowDep) -> TaskService:
    """Build a TaskService for the current request."""
    return TaskService(uow)


def get_user_service(uow: UowDep) -> UserService:
    """Build a UserService for the current request."""
    return UserService(uow)


def get_auth_service(uow: UowDep) -> AuthService:
    """Build an AuthService for the current request."""
    return AuthService(uow)


def get_workspace_service(uow: UowDep) -> WorkspaceService:
    """Build a WorkspaceService for the current request."""
    return WorkspaceService(uow)


def get_workspace_member_service(uow: UowDep) -> WorkspaceMemberService:
    """Build a WorkspaceMemberService for the current request."""
    return WorkspaceMemberService(uow)


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]
WorkspaceMemberServiceDep = Annotated[
    WorkspaceMemberService, Depends(get_workspace_member_service)
]


async def get_current_user(
    request: Request,
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: AuthServiceDep,
) -> AsyncGenerator[UserRead, None]:
    """Resolve the bearer token to a user and set actor context for the request."""
    user = await auth_service.get_user_from_token(token)
    actor_id = str(user.id)
    request.state.actor_id = actor_id
    actor_ctx = current_user_id_ctx.set(actor_id)
    try:
        yield user
    finally:
        current_user_id_ctx.reset(actor_ctx)


CurrentUserDep = Annotated[UserRead, Depends(get_current_user)]
