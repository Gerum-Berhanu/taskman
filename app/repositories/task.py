"""Task persistence."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core import timeutils as tu
from app.models.task import Task


class TaskRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    status: str
    due_date: datetime | None
    workspace_id: UUID
    assigned_user_id: UUID | None
    created_at: datetime
    updated_at: datetime | None


class TaskCreateData(BaseModel):
    title: str
    description: str | None = None
    due_date: datetime | None = None
    workspace_id: UUID
    assigned_user_id: UUID | None = None


class TaskUpdateData(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    due_date: datetime | None = None
    assigned_user_id: UUID | None = None


def _to_record(task: Task) -> TaskRecord:
    return TaskRecord.model_validate(task)


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        fields: TaskCreateData,
    ) -> TaskRecord:
        task = Task(**fields.model_dump())
        self._session.add(task)
        await self._session.flush()
        await self._session.refresh(task)
        return _to_record(task)

    async def _get_task_orm(self, *, workspace_id: UUID, task_id: UUID) -> Task | None:
        statement = select(Task).where(
            Task.id == task_id, Task.workspace_id == workspace_id
        )
        result = await self._session.exec(statement)
        return result.first()

    async def get(self, workspace_id: UUID, task_id: UUID) -> TaskRecord | None:
        task = await self._get_task_orm(workspace_id=workspace_id, task_id=task_id)
        if task is None:
            return None
        return _to_record(task)

    async def list_all(self, workspace_id: UUID) -> list[TaskRecord]:
        statement = select(Task).where(Task.workspace_id == workspace_id)
        result = await self._session.exec(statement)
        return [_to_record(task) for task in result.all()]

    async def update(
        self, task_id: UUID, workspace_id: UUID, fields: TaskUpdateData
    ) -> TaskRecord | None:
        task = await self._get_task_orm(workspace_id=workspace_id, task_id=task_id)
        if task is None:
            return None

        updates = fields.model_dump(exclude_unset=True)
        if not updates:
            return TaskRecord.model_validate(task)

        for key, value in updates.items():
            setattr(task, key, value)
        task.updated_at = tu.utcnow()

        self._session.add(task)
        await self._session.flush()
        await self._session.refresh(task)
        return TaskRecord.model_validate(task)

    async def delete(self, task_id: UUID, workspace_id: UUID) -> bool:
        task = await self._get_task_orm(workspace_id=workspace_id, task_id=task_id)
        if task is None:
            return False
        await self._session.delete(task)
        await self._session.flush()
        return True
