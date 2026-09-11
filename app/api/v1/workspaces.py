"""Workspaces HTTP endpoints."""

from fastapi import APIRouter, Depends
from pydantic import UUID4
from starlette.status import HTTP_201_CREATED

from app.deps import (
    CurrentUserDep, 
    WorkspaceServiceDep, 
    get_current_user, 
)
from app.rbac import RequireRole
from app.repositories import WorkspaceRecord
from app.repositories.workspace import WorkspaceMemberRecord
from app.schemas.workspace import (
    WorkspaceCreate, 
    WorkspaceMemberCreate, 
    WorkspaceMemberRead,
    WorkspaceMemberRole, 
    WorkspaceRead
)

router = APIRouter(
    prefix="/workspaces",
    tags=["workspaces"],
    dependencies=[Depends(get_current_user)]
)


@router.post("", response_model=WorkspaceRead, status_code=HTTP_201_CREATED)
async def create_workspace(
    new_workspace: WorkspaceCreate,
    current_user: CurrentUserDep,
    workspace_service: WorkspaceServiceDep,
) -> WorkspaceRecord:
    return await workspace_service.create_workspace(new_workspace, current_user.id)


@router.post(
    "/{workspace_id}/members", 
    response_model=WorkspaceMemberRead, 
    status_code=HTTP_201_CREATED,
    dependencies=[Depends(RequireRole(WorkspaceMemberRole.OWNER))]
)
async def create_membership(
    workspace_id: UUID4, 
    new_membership: WorkspaceMemberCreate,
    workspace_service: WorkspaceServiceDep,
) -> WorkspaceMemberRecord:
    return await workspace_service.create_membership(workspace_id, new_membership)
