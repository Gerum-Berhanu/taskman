from uuid import UUID

from app.core.exceptions import TaskNotFoundError
from app.database.unit_of_work import UnitOfWork
from app.repositories.task import TaskCreateData, TaskRecord, TaskUpdateData
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def create(self, data: TaskCreate, workspace_id: UUID) -> TaskRecord:
        fields = TaskCreateData(**data.model_dump(), workspace_id=workspace_id)
        return await self._uow.tasks.create(fields=fields)

    async def get(self, workspace_id: UUID, task_id: UUID) -> TaskRecord:
        task = await self._uow.tasks.get(workspace_id, task_id)
        if not task:
            raise TaskNotFoundError
        return task

    async def list_all(self, workspace_id: UUID) -> list[TaskRecord]:
        return await self._uow.tasks.list_all(workspace_id)

    async def update(self, task_id: UUID, workspace_id: UUID, data: TaskUpdate) -> TaskRecord:
        task = await self._uow.tasks.update(
            task_id,
            workspace_id,
            TaskUpdateData(**data.model_dump(exclude_unset=True))
        )
        if task is None:
            raise TaskNotFoundError
        return task

    async def delete(self, task_id: UUID, workspace_id: UUID) -> None:
        if not await self._uow.tasks.delete(task_id, workspace_id):
            raise TaskNotFoundError
