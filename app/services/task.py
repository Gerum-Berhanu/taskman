"""Workspace-scoped task application services."""

import logging
from uuid import UUID

from fastapi import BackgroundTasks
from pydantic import UUID4

from app.core.exceptions import (
    AssigneeNotInWorkspaceError,
    TaskNotFoundError,
    UserNotFoundError,
)
from app.core.request_context import current_user_id_ctx
from app.infrastructure.export.task_export import run_tasks_export
from app.infrastructure.redis.cache import delete_keys, get_json, set_json, task_summary_key
from app.repositories.unit_of_work import UnitOfWork
from app.repositories.task import TaskCreateData, TaskRecord, TaskUpdateData
from app.schemas.task import TaskCreate, TaskSummaryRead, TaskUpdate


logger = logging.getLogger(__name__)


class TaskService:
    """Create, read, update, and delete tasks within a workspace."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def _validate_assignee(
        self, workspace_id: UUID, assigned_user_id: UUID4 | None
    ) -> None:
        """Ensure an assignee exists and belongs to the workspace (no-op if None)."""
        if assigned_user_id is None:
            return
        if await self._uow.users.get(assigned_user_id) is None:
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
        await self._invalidate_summary(workspace_id)
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
        await self._invalidate_summary(workspace_id)
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
        await self._invalidate_summary(workspace_id)

    async def summary(self, workspace_id: UUID) -> dict[str, UUID | int]:
        key = task_summary_key(workspace_id)

        try:
            cached = await get_json(key)
            if cached is not None:
                # cached workspace_id is a str; response_model coerces to UUID4
                return cached
        except Exception:
            logger.exception("cache_backend_error op=get key=%s", key)

        status_count = await self._uow.tasks.count_by_status(workspace_id)
        summary = {
            "workspace_id": workspace_id,
            "total": sum(status_count.values()),
            **status_count,
        }

        try:
            await set_json(
                key,
                {**summary, "workspace_id": str(workspace_id)},
            )
        except Exception:
            logger.exception("cache_backend_error op=set key=%s", key)

        return summary

    async def _invalidate_summary(self, workspace_id: UUID) -> None:
        """Early invalidate is fine (worst case: extra DB read if commit fails)."""
        key = task_summary_key(workspace_id)
        try:
            await delete_keys(key)
        except Exception:
            logger.exception(
                "cache_backend_error op=delete key=%s workspace_id=%s",
                key,
                workspace_id,
            )

    async def export(
        self,
        workspace_id: UUID,
        *,
        to_email: str,
        bg_tasks: BackgroundTasks,
    ) -> None:
        actor_id = current_user_id_ctx.get()
        bg_tasks.add_task(
            run_tasks_export,
            workspace_id=workspace_id,
            to_email=to_email,
            actor_id=actor_id,
        )
