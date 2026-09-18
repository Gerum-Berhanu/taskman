"""Task persistence."""

from datetime import datetime
from uuid import UUID

from pydantic import UUID4, BaseModel, ConfigDict
from sqlmodel import col, select

from app.core import timeutils as tu
from app.models.task import Task
from app.repositories.base import BaseRepository


class TaskRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    title: str
    description: str | None
    status: str
    due_date: datetime | None
    workspace_id: UUID4
    assigned_user_id: UUID4 | None
    created_at: datetime
    updated_at: datetime | None


class TaskCreateData(BaseModel):
    title: str
    description: str | None = None
    due_date: datetime | None = None
    workspace_id: UUID4
    assigned_user_id: UUID4 | None = None


class TaskUpdateData(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    due_date: datetime | None = None
    assigned_user_id: UUID4 | None = None


class TaskRepository(BaseRepository):
    async def create(self, fields: TaskCreateData) -> TaskRecord:
        """Insert a task and return the persisted record."""
        task = Task(**fields.model_dump(), updated_at=tu.utcnow())
        await self.add_flush_refresh(task)
        return self.to_record(TaskRecord, task)

    async def _get_task_orm(self, *, workspace_id: UUID, task_id: UUID) -> Task | None:
        """Load the ORM task scoped to a workspace, or None."""
        statement = select(Task).where(
            Task.id == task_id, Task.workspace_id == workspace_id
        )
        result = await self._session.exec(statement)
        return result.first()

    async def get(self, workspace_id: UUID, task_id: UUID) -> TaskRecord | None:
        """Fetch a task by id within a workspace, or None."""
        task = await self._get_task_orm(workspace_id=workspace_id, task_id=task_id)
        if task is None:
            return None
        return self.to_record(TaskRecord, task)

    async def list_all(self, workspace_id: UUID) -> list[TaskRecord]:
        """List tasks in a workspace ordered by created_at, title, id."""
        statement = (
            select(Task)
            .where(Task.workspace_id == workspace_id)
            .order_by(col(Task.created_at), col(Task.title), col(Task.id))
        )
        result = await self._session.exec(statement)
        return [self.to_record(TaskRecord, task) for task in result.all()]

    async def update(
        self, workspace_id: UUID, task_id: UUID, fields: TaskUpdateData
    ) -> TaskRecord | None:
        """Apply partial updates to a workspace-scoped task; None if missing."""
        task = await self._get_task_orm(workspace_id=workspace_id, task_id=task_id)
        if task is None:
            return None

        updates = fields.model_dump(exclude_unset=True)
        if not updates:
            return self.to_record(TaskRecord, task)

        for key, value in updates.items():
            setattr(task, key, value)
        task.updated_at = tu.utcnow()

        await self.flush_refresh(task)
        return self.to_record(TaskRecord, task)

    async def delete(self, workspace_id: UUID, task_id: UUID) -> bool:
        """Delete a workspace-scoped task; False if it did not exist."""
        task = await self._get_task_orm(workspace_id=workspace_id, task_id=task_id)
        if task is None:
            return False
        await self._session.delete(task)
        await self._session.flush()
        return True
