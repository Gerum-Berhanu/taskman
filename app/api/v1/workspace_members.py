"""Workspace members HTTP endpoints."""

from fastapi import APIRouter, Depends
from pydantic import UUID4
from starlette.status import HTTP_201_CREATED

from app.deps import WorkspaceMemberServiceDep, get_current_user
from app.rbac import RequireRole
from app.repositories import WorkspaceMemberRecord
from app.schemas.workspace import WorkspaceMemberCreate, WorkspaceMemberRead, WorkspaceMemberRole


router = APIRouter(
    prefix="/workspaces",
    tags=["workspaces"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberRead,
    status_code=HTTP_201_CREATED,
    dependencies=[Depends(RequireRole(WorkspaceMemberRole.OWNER))],
)
async def add_workspace_member(
    workspace_id: UUID4,
    new_membership: WorkspaceMemberCreate,
    member_service: WorkspaceMemberServiceDep,
) -> WorkspaceMemberRecord:
    return await member_service.create(workspace_id, new_membership)
