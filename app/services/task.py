from uuid import UUID

from app.core.exceptions import TaskNotFoundError
from app.database.unit_of_work import UnitOfWork
from app.repositories.records import TaskRecord, TaskUpdateData
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def create(self, data: TaskCreate) -> TaskRecord:
        return await self._uow.tasks.create(**data.model_dump())

    async def get(self, task_id: UUID) -> TaskRecord:
        task = await self._uow.tasks.get(task_id)
        if not task:
            raise TaskNotFoundError
        return task

    async def list_all(self) -> list[TaskRecord]:
        return await self._uow.tasks.list_all()

    async def update(self, task_id: UUID, data: TaskUpdate) -> TaskRecord:
        task = await self._uow.tasks.update(
            task_id,
            TaskUpdateData(**data.model_dump(exclude_unset=True))
        )
        if task is None:
            raise TaskNotFoundError
        return task

    async def delete(self, task_id: UUID) -> None:
        if not await self._uow.tasks.delete(task_id):
            raise TaskNotFoundError
