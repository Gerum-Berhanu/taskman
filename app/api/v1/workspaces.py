"""Workspaces HTTP endpoints."""

from fastapi import APIRouter, Depends
from starlette.status import HTTP_201_CREATED

from app.deps import CurrentUserDep, WorkspaceServiceDep, get_current_user
from app.repositories import WorkspaceRecord
from app.schemas.workspace import WorkspaceCreate, WorkspaceRead

router = APIRouter(
    prefix="/workspaces",
    tags=["workspaces"],
    dependencies=[Depends(get_current_user)],
)


@router.post("", response_model=WorkspaceRead, status_code=HTTP_201_CREATED)
async def create_workspace(
    new_workspace: WorkspaceCreate,
    current_user: CurrentUserDep,
    workspace_service: WorkspaceServiceDep,
) -> WorkspaceRecord:
    return await workspace_service.create(new_workspace, current_user.id)
