"""Tasks HTTP endpoints."""

from fastapi import APIRouter, Depends
from starlette.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT

from app.database.records import TaskRecord
from app.deps import TaskDep, TaskServiceDep, get_current_user
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    dependencies=[Depends(get_current_user)],
)


@router.post("", response_model=TaskRead, status_code=HTTP_201_CREATED)
async def create_task(new_task: TaskCreate, service: TaskServiceDep) -> TaskRecord:
    return service.create(new_task)


@router.get("/{task_id}", response_model=TaskRead)
async def read_task_by_id(task: TaskDep) -> TaskRecord:
    return task


@router.get("", response_model=list[TaskRead])
async def read_all_tasks(service: TaskServiceDep) -> list[TaskRecord]:
    return service.list_all()


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(
    task: TaskDep,
    task_in: TaskUpdate,
    service: TaskServiceDep,
) -> TaskRecord:
    return service.update(task["id"], task_in)


@router.delete("/{task_id}", status_code=HTTP_204_NO_CONTENT)
async def delete_task(task: TaskDep, service: TaskServiceDep) -> None:
    service.delete(task["id"])
