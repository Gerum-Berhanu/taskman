import logging
from uuid import UUID

from app.core.exceptions import (
    AssigneeNotInWorkspaceError,
    TaskNotFoundError,
    UserNotFoundError,
)
from app.core.request_context import current_user_id_ctx
from app.database.unit_of_work import UnitOfWork
from app.repositories.task import TaskCreateData, TaskRecord, TaskUpdateData
from app.schemas.task import TaskCreate, TaskUpdate


logger = logging.getLogger(__name__)


class TaskService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def _validate_assignee(
        self, workspace_id: UUID, assigned_user_id: UUID | None
    ) -> None:
        """Ensure an assignee exists and belongs to the workspace (no-op if None)."""
        if assigned_user_id is None:
            return
        if await self._uow.users.get_by_id(assigned_user_id) is None:
            raise UserNotFoundError
        member = await self._uow.workspace_members.get(
            workspace_id, assigned_user_id
        )
        if member is None:
            raise AssigneeNotInWorkspaceError

    async def create(self, data: TaskCreate, workspace_id: UUID) -> TaskRecord:
        """Create a task in the workspace after validating the optional assignee."""
        await self._validate_assignee(workspace_id, data.assigned_user_id)
        fields = TaskCreateData(**data.model_dump(), workspace_id=workspace_id)
        task = await self._uow.tasks.create(fields)
        task_id = task.id
        actor_id = current_user_id_ctx.get()
        self._uow.after_commit(
            lambda: logger.info(
                "task_created workspace_id=%s task_id=%s actor_id=%s",
                workspace_id,
                task_id,
                actor_id,
            )
        )
        return task

    async def get(self, workspace_id: UUID, task_id: UUID) -> TaskRecord:
        """Return a task in the workspace or raise not-found."""
        task = await self._uow.tasks.get(workspace_id, task_id)
        if not task:
            raise TaskNotFoundError
        return task

    async def list_all(self, workspace_id: UUID) -> list[TaskRecord]:
        """List all tasks in the workspace."""
        return await self._uow.tasks.list_all(workspace_id)

    async def update(
        self, workspace_id: UUID, task_id: UUID, data: TaskUpdate
    ) -> TaskRecord:
        """Update a task; exist-check before assignee validation."""
        if await self._uow.tasks.get(workspace_id, task_id) is None:
            raise TaskNotFoundError

        updates = data.model_dump(exclude_unset=True)
        if "assigned_user_id" in updates:
            await self._validate_assignee(workspace_id, updates["assigned_user_id"])

        task = await self._uow.tasks.update(
            workspace_id,
            task_id,
            TaskUpdateData(**updates),
        )
        if task is None:
            raise TaskNotFoundError

        actor_id = current_user_id_ctx.get()
        self._uow.after_commit(
            lambda: logger.info(
                "task_updated workspace_id=%s task_id=%s actor_id=%s",
                workspace_id,
                task_id,
                actor_id,
            )
        )
        return task

    async def delete(self, workspace_id: UUID, task_id: UUID) -> None:
        """Delete a task in the workspace or raise not-found."""
        if not await self._uow.tasks.delete(workspace_id, task_id):
            raise TaskNotFoundError
        actor_id = current_user_id_ctx.get()
        self._uow.after_commit(
            lambda: logger.info(
                "task_deleted workspace_id=%s task_id=%s actor_id=%s",
                workspace_id,
                task_id,
                actor_id,
            )
        )
