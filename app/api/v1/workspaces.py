"""Workspaces HTTP endpoints."""

from fastapi import APIRouter, Depends
from pydantic import UUID4
from starlette.status import HTTP_201_CREATED

from app.deps import CurrentUserDep, WorkspaceMemberServiceDep, WorkspaceServiceDep, get_current_user
from app.dto.api import WorkspaceMemberCreate, WorkspaceMemberRead, WorkspaceMemberRole
from app.dto.api.workspace import WorkspaceCreate, WorkspaceRead
from app.rbac import RequireRole

router = APIRouter(
    prefix="/workspaces",
    tags=["workspaces"],
    dependencies=[Depends(get_current_user)],
)


@router.post("", response_model=WorkspaceRead, status_code=HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate,
    current_user: CurrentUserDep,
    workspace_service: WorkspaceServiceDep,
) -> WorkspaceRead:
    return await workspace_service.create(payload, current_user.id)


@router.get("", response_model=list[WorkspaceRead])
async def list_workspaces(
    current_user: CurrentUserDep,
    workspace_service: WorkspaceServiceDep,
) -> list[WorkspaceRead]:
    return await workspace_service.list_by_user(current_user.id)


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberRead,
    status_code=HTTP_201_CREATED,
    dependencies=[Depends(RequireRole(WorkspaceMemberRole.OWNER))],
)
async def add_workspace_member(
    workspace_id: UUID4,
    payload: WorkspaceMemberCreate,
    member_service: WorkspaceMemberServiceDep,
) -> WorkspaceMemberRead:
    return await member_service.create(workspace_id, payload)
