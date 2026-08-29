from pydantic import UUID4

from app.core.exceptions import TaskNotFoundError
from app.repositories.records import TaskRecord
from app.repositories.task_repo import TaskRepository
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    async def create(self, data: TaskCreate) -> TaskRecord:
        return await self._repository.create(data.model_dump())

    async def get(self, task_id: UUID4) -> TaskRecord:
        task = await self._repository.get(task_id)
        if not task:
            raise TaskNotFoundError
        return task

    async def list_all(self) -> list[TaskRecord]:
        return await self._repository.list_all()

    async def update(self, task_id: UUID4, data: TaskUpdate) -> TaskRecord:
        task = await self._repository.update(task_id, data.model_dump(exclude_unset=True))
        if task is None:
            raise TaskNotFoundError
        return task

    async def delete(self, task_id: UUID4) -> None:
        if not await self._repository.delete(task_id):
            raise TaskNotFoundError
