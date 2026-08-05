"""Tasks HTTP endpoints."""

from fastapi import APIRouter
from starlette.status import HTTP_201_CREATED

from app.schemas import TaskCreate, TaskRead
import app.storage as st

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("", response_model=TaskRead, status_code=HTTP_201_CREATED)
async def create_task(new_task: TaskCreate) -> dict:
    return st.create(new_task.model_dump())