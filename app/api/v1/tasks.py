"""Tasks HTTP endpoints."""

from fastapi import APIRouter, Depends
from pydantic import UUID4
from starlette.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT

from app.core.rate_limit_policies import TASK_READS_POLICY, TASK_WRITES_POLICY
from app.rbac import RequireRole
from app.repositories.task import TaskRecord
from app.deps import TaskServiceDep, get_current_user
from app.http.dependencies.rate_limit import rate_limit
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.schemas.workspace_member import WorkspaceMemberRole

router = APIRouter(
    prefix="/workspaces/{workspace_id}/tasks",
    tags=["tasks"],
    dependencies=[Depends(get_current_user)],
)


VIEWER = WorkspaceMemberRole.VIEWER
EDITOR = WorkspaceMemberRole.EDITOR
OWNER = WorkspaceMemberRole.OWNER


@router.post(
    "", 
    response_model=TaskRead, 
    status_code=HTTP_201_CREATED, 
    dependencies=[Depends(RequireRole(EDITOR)), rate_limit(TASK_WRITES_POLICY)],
)
async def create_task(
    new_task: TaskCreate, workspace_id: UUID4, task_service: TaskServiceDep
) -> TaskRecord:
    return await task_service.create(new_task, workspace_id)


@router.get(
    "/{task_id}",
    response_model=TaskRead,
    dependencies=[Depends(RequireRole(VIEWER)), rate_limit(TASK_READS_POLICY)],
)
async def get_task_by_id(workspace_id: UUID4, task_id: UUID4, service: TaskServiceDep) -> TaskRecord:
    return await service.get(workspace_id, task_id)


@router.get(
    "",
    response_model=list[TaskRead],
    dependencies=[Depends(RequireRole(VIEWER)), rate_limit(TASK_READS_POLICY)],
)
async def list_by_workspace(workspace_id: UUID4, service: TaskServiceDep) -> list[TaskRecord]:
    return await service.list_all(workspace_id)


@router.patch(
    "/{task_id}",
    response_model=TaskRead,
    dependencies=[Depends(RequireRole(EDITOR)), rate_limit(TASK_WRITES_POLICY)],
)
async def update_task(
    workspace_id: UUID4,
    task_id: UUID4,
    task_in: TaskUpdate,
    service: TaskServiceDep,
) -> TaskRecord:
    return await service.update(workspace_id, task_id, task_in)


@router.delete(
    "/{task_id}",
    status_code=HTTP_204_NO_CONTENT,
    dependencies=[Depends(RequireRole(OWNER)), rate_limit(TASK_WRITES_POLICY)],
)
async def delete_task(workspace_id: UUID4, task_id: UUID4, service: TaskServiceDep) -> None:
    await service.delete(workspace_id, task_id)
