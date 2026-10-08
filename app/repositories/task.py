"""Task persistence."""

from uuid import UUID

from sqlmodel import col, func, select

from app.core.timeutils import utcnow
from app.models.task import Task
from app.repositories.base import BaseRepository
from app.dto.repository import TaskCreateData, TaskRecord, TaskUpdateData


class TaskRepository(BaseRepository[Task, TaskRecord, TaskCreateData]):
    model = Task
    record = TaskRecord

    async def _get_orm(self, *, workspace_id: UUID, task_id: UUID) -> Task | None:
        """Load the ORM task scoped to a workspace, or None."""
        statement = select(Task).where(
            Task.id == task_id, Task.workspace_id == workspace_id
        )
        result = await self._session.exec(statement)
        return result.first()

    async def get(self, workspace_id: UUID, task_id: UUID) -> TaskRecord | None:
        """Fetch a task by id within a workspace, or None."""
        task = await self._get_orm(workspace_id=workspace_id, task_id=task_id)
        if task is None:
            return None
        return self._to_record(task)

    async def list_all(self, workspace_id: UUID) -> list[TaskRecord]:
        """List tasks in a workspace ordered by created_at, title, id."""
        statement = (
            select(Task)
            .where(Task.workspace_id == workspace_id)
            .order_by(col(Task.created_at), col(Task.title), col(Task.id))
        )
        result = await self._session.exec(statement)
        return [self._to_record(task) for task in result.all()]

    async def update(
        self, workspace_id: UUID, task_id: UUID, fields: TaskUpdateData
    ) -> TaskRecord | None:
        """Apply partial updates to a workspace-scoped task; None if missing."""
        task = await self._get_orm(workspace_id=workspace_id, task_id=task_id)
        if task is None:
            return None

        updates = fields.model_dump(exclude_unset=True)
        if not updates:
            return self._to_record(task)

        for key, value in updates.items():
            setattr(task, key, value)
        task.updated_at = utcnow()

        await self._flush_refresh(task)
        return self._to_record(task)

    async def delete(self, workspace_id: UUID, task_id: UUID) -> bool:
        """Delete a workspace-scoped task; False if it did not exist."""
        task = await self._get_orm(workspace_id=workspace_id, task_id=task_id)
        if task is None:
            return False
        await self._session.delete(task)
        await self._session.flush()
        return True

    async def count_by_status(self, workspace_id: UUID) -> dict[str, int]:
        statement = (
            select(Task.status, func.count())
            .where(Task.workspace_id == workspace_id)
            .group_by(col(Task.status))
        )
        result = await self._session.exec(statement)
        counts = {status: 0 for status in ("pending", "in_progress", "completed")}
        for status, n in result.all():
            if status in counts:
                counts[status] = int(n)
        return counts
