"""Tasks HTTP endpoints."""

from fastapi import APIRouter, Depends
from pydantic import UUID4
from starlette.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT

from app.repositories.records import TaskRecord
from app.deps import TaskServiceDep, get_current_user
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    dependencies=[Depends(get_current_user)],
)


@router.post("", response_model=TaskRead, status_code=HTTP_201_CREATED)
async def create_task(new_task: TaskCreate, service: TaskServiceDep) -> TaskRecord:
    return await service.create(new_task)


@router.get("/{task_id}", response_model=TaskRead)
async def read_task_by_id(task_id: UUID4, service: TaskServiceDep) -> TaskRecord:
    return await service.get(task_id)


@router.get("", response_model=list[TaskRead])
async def read_all_tasks(service: TaskServiceDep) -> list[TaskRecord]:
    return await service.list_all()


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: UUID4,
    task_in: TaskUpdate,
    service: TaskServiceDep,
) -> TaskRecord:
    return await service.update(task_id, task_in)


@router.delete("/{task_id}", status_code=HTTP_204_NO_CONTENT)
async def delete_task(task_id: UUID4, service: TaskServiceDep) -> None:
    await service.delete(task_id)
