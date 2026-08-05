"""Tasks HTTP endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import UUID4
from starlette.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND

from app.schemas import TaskCreate, TaskRead
import app.storage as st

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskRead, status_code=HTTP_201_CREATED)
async def create_task(new_task: TaskCreate) -> dict:
    return st.create(new_task.model_dump())


@router.get("/{task_id}", response_model=TaskRead)
async def read_task_by_id(task_id: UUID4) -> dict:
    task = st.get(task_id)
    if task is None:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Task not found"
        )
    return task
