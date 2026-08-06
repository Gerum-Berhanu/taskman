"""Tasks HTTP endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import UUID4
from starlette.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_404_NOT_FOUND

from app.schemas import TaskCreate, TaskRead, TaskUpdate
import app.storage as st

router = APIRouter(prefix="/tasks", tags=["tasks"])

def get_task_or_404(task_id: UUID4):
    task = st.get(task_id)
    if task is None:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return task


@router.post("", response_model=TaskRead, status_code=HTTP_201_CREATED)
async def create_task(new_task: TaskCreate) -> dict:
    return st.create(new_task.model_dump())


@router.get("/{task_id}", response_model=TaskRead)
async def read_task_by_id(task_id: UUID4) -> dict:
    return get_task_or_404(task_id)


@router.get("", response_model=list[TaskRead])
async def read_all_tasks() -> list[dict]:
    return st.list_all()


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(task_id: UUID4, task_in: TaskUpdate) -> dict:
    get_task_or_404(task_id)
    return st.update(task_id, task_in.model_dump(exclude_unset=True))


@router.delete("/{task_id}", status_code=HTTP_204_NO_CONTENT)
async def delete_task(task_id: UUID4):
    get_task_or_404(task_id)
    st.delete(task_id)