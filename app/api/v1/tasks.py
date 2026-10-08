"""Tasks HTTP endpoints."""

from fastapi import APIRouter, BackgroundTasks, Depends, Response
from pydantic import UUID4
from starlette.status import HTTP_201_CREATED, HTTP_202_ACCEPTED, HTTP_204_NO_CONTENT

from app.rbac import RequireRole
from app.deps import CurrentUserDep, TaskServiceDep, get_current_user
from app.dto.api.task import TaskCreate, TaskRead, TaskSummaryRead, TaskUpdate
from app.dto.api.workspace_member import WorkspaceMemberRole

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
    dependencies=[Depends(RequireRole(EDITOR))],
)
async def create_task(
    payload: TaskCreate, workspace_id: UUID4, task_service: TaskServiceDep
) -> TaskRead:
    return await task_service.create(payload, workspace_id)


@router.get(
    "/summary", response_model=TaskSummaryRead, dependencies=[Depends(RequireRole(VIEWER))]
)
async def get_task_summary(
    workspace_id: UUID4, task_service: TaskServiceDep
) -> TaskSummaryRead:
    return await task_service.summary(workspace_id)


@router.post(
    "/export",
    status_code=HTTP_202_ACCEPTED,
    response_class=Response,
    dependencies=[Depends(RequireRole(VIEWER))],
)
async def export_tasks(
    workspace_id: UUID4,
    task_service: TaskServiceDep,
    current_user: CurrentUserDep,
    bg_tasks: BackgroundTasks,
) -> Response:
    await task_service.export(
        workspace_id,
        to_email=current_user.email,
        bg_tasks=bg_tasks,
    )
    return Response(status_code=HTTP_202_ACCEPTED)


@router.get("/{task_id}", response_model=TaskRead, dependencies=[Depends(RequireRole(VIEWER))])
async def get_task(
    workspace_id: UUID4, task_id: UUID4, task_service: TaskServiceDep
) -> TaskRead:
    return await task_service.get(workspace_id, task_id)


@router.get("", response_model=list[TaskRead], dependencies=[Depends(RequireRole(VIEWER))])
async def list_tasks(
    workspace_id: UUID4, task_service: TaskServiceDep
) -> list[TaskRead]:
    return await task_service.list_all(workspace_id)


@router.patch("/{task_id}", response_model=TaskRead, dependencies=[Depends(RequireRole(EDITOR))])
async def update_task(
    workspace_id: UUID4,
    task_id: UUID4,
    payload: TaskUpdate,
    task_service: TaskServiceDep,
) -> TaskRead:
    return await task_service.update(workspace_id, task_id, payload)


@router.delete(
    "/{task_id}", status_code=HTTP_204_NO_CONTENT, dependencies=[Depends(RequireRole(OWNER))]
)
async def delete_task(
    workspace_id: UUID4, task_id: UUID4, task_service: TaskServiceDep
) -> None:
    await task_service.delete(workspace_id, task_id)
