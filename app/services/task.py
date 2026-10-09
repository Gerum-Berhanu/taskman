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
from app.dto.api.task import TaskCreate, TaskRead, TaskSummaryRead, TaskUpdate
from app.dto.repository import TaskCreateData, TaskRecord, TaskUpdateData
from app.observability.events import DomainLogEvent
from app.observability.log_event import log_event
from app.repositories.unit_of_work import UnitOfWork


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
        membership = await self._uow.workspace_members.get(
            workspace_id, assigned_user_id
        )
        if membership is None:
            raise AssigneeNotInWorkspaceError

    @staticmethod
    def _to_read(record: TaskRecord) -> TaskRead:
        return TaskRead.model_validate(record, from_attributes=True)

    async def create(self, payload: TaskCreate, workspace_id: UUID) -> TaskRead:
        """Create a task in the workspace after validating the optional assignee."""
        await self._validate_assignee(workspace_id, payload.assigned_user_id)
        fields = TaskCreateData(**payload.model_dump(), workspace_id=workspace_id)
        task = await self._uow.tasks.create(fields)
        task_id = task.id
        actor_id = current_user_id_ctx.get()
        self._uow.after_commit(
            lambda: log_event(
                logger,
                logging.INFO,
                DomainLogEvent.TASK_CREATED,
                workspace_id=workspace_id,
                task_id=task_id,
                actor_id=actor_id,
            )
        )
        await self._invalidate_summary(workspace_id)
        return self._to_read(task)

    async def get(self, workspace_id: UUID, task_id: UUID) -> TaskRead:
        """Return a task in the workspace or raise not-found."""
        task = await self._uow.tasks.get(workspace_id, task_id)
        if not task:
            raise TaskNotFoundError
        return self._to_read(task)

    async def list_all(self, workspace_id: UUID) -> list[TaskRead]:
        """List all tasks in the workspace."""
        tasks = await self._uow.tasks.list_all(workspace_id)
        return [self._to_read(task) for task in tasks]

    async def update(
        self, workspace_id: UUID, task_id: UUID, payload: TaskUpdate
    ) -> TaskRead:
        """Update a task; exist-check before assignee validation."""
        if await self._uow.tasks.get(workspace_id, task_id) is None:
            raise TaskNotFoundError

        updates = payload.model_dump(exclude_unset=True)
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
            lambda: log_event(
                logger,
                logging.INFO,
                DomainLogEvent.TASK_UPDATED,
                workspace_id=workspace_id,
                task_id=task_id,
                actor_id=actor_id,
            )
        )
        await self._invalidate_summary(workspace_id)
        return self._to_read(task)

    async def delete(self, workspace_id: UUID, task_id: UUID) -> None:
        """Delete a task in the workspace or raise not-found."""
        if not await self._uow.tasks.delete(workspace_id, task_id):
            raise TaskNotFoundError
        actor_id = current_user_id_ctx.get()
        self._uow.after_commit(
            lambda: log_event(
                logger,
                logging.INFO,
                DomainLogEvent.TASK_DELETED,
                workspace_id=workspace_id,
                task_id=task_id,
                actor_id=actor_id,
            )
        )
        await self._invalidate_summary(workspace_id)

    async def summary(self, workspace_id: UUID) -> TaskSummaryRead:
        key = task_summary_key(workspace_id)

        try:
            cached = await get_json(key)
            if cached is not None:
                return TaskSummaryRead.model_validate(cached)
        except Exception:
            log_event(
                logger,
                logging.ERROR,
                DomainLogEvent.CACHE_BACKEND_ERROR,
                exc_info=True,
                op="get",
                key=key,
            )

        status_count = await self._uow.tasks.count_by_status(workspace_id)
        summary = TaskSummaryRead(
            workspace_id=workspace_id,
            total=sum(status_count.values()),
            **status_count,
        )

        try:
            await set_json(
                key,
                {**summary.model_dump(mode="json"), "workspace_id": str(workspace_id)},
            )
        except Exception:
            log_event(
                logger,
                logging.ERROR,
                DomainLogEvent.CACHE_BACKEND_ERROR,
                exc_info=True,
                op="set",
                key=key,
            )

        return summary

    async def _invalidate_summary(self, workspace_id: UUID) -> None:
        """Early invalidate is fine (worst case: extra DB read if commit fails)."""
        key = task_summary_key(workspace_id)
        try:
            await delete_keys(key)
        except Exception:
            log_event(
                logger,
                logging.ERROR,
                DomainLogEvent.CACHE_BACKEND_ERROR,
                exc_info=True,
                op="delete",
                key=key,
                workspace_id=workspace_id,
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
