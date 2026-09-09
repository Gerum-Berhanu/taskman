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
    created_at: datetime
    updated_at: datetime | None


class TaskUpdateData(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    due_date: datetime | None = None


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        title: str,
        description: str | None = None,
        due_date: datetime | None = None,
    ) -> TaskRecord:
        task = Task(title=title, description=description, due_date=due_date)
        self._session.add(task)
        await self._session.flush()
        await self._session.refresh(task)
        return TaskRecord.model_validate(task)

    async def get(self, task_id: UUID) -> TaskRecord | None:
        task = await self._session.get(Task, task_id)
        if task is None:
            return None
        return TaskRecord.model_validate(task)

    async def list_all(self) -> list[TaskRecord]:
        result = await self._session.exec(select(Task))
        return [TaskRecord.model_validate(task) for task in result.all()]

    async def update(
        self, task_id: UUID, fields: TaskUpdateData
    ) -> TaskRecord | None:
        task = await self._session.get(Task, task_id)
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

    async def delete(self, task_id: UUID) -> bool:
        task = await self._session.get(Task, task_id)
        if task is None:
            return False
        await self._session.delete(task)
        await self._session.flush()
        return True
