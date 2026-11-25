"""Workspace-scoped task application services."""

from logging import ERROR, INFO, getLogger
from uuid import UUID

from celery.exceptions import OperationalError
from pydantic import ValidationError

from app.exceptions import (
    AssigneeNotInWorkspaceError,
    ServiceUnavailableError,
    TaskNotFoundError,
)
from app.core.request_context import current_user_id_ctx
from app.infrastructure.redis.cache import (
    get_cached_summary,
    invalidate_summary_cache,
    set_cached_summary,
)
from app.dto.api.task import TaskCreate, TaskRead, TaskSummaryRead, TaskUpdate
from app.dto.repository import TaskCreateData, TaskRecord, TaskUpdateData
from app.observability.events.domain import (
    CACHE_BACKEND_ERROR,
    TASKS_CREATED,
    TASKS_DELETED,
    TASK_UPDATED,
)
from app.observability.log_event import log_event
from app.services.base import BaseService
from app.workers.tasks import export_workspace_tasks


logger = getLogger(__name__)


class TaskService(BaseService):
    """Create, read, update, and delete tasks within a workspace."""

    def _to_read(self, record: TaskRecord) -> TaskRead:
        return TaskRead.model_validate(record, from_attributes=True)

    async def _assert_assignees_in_workspace(
        self, workspace_id: UUID, user_ids: set[UUID]
    ) -> None:
        if not user_ids:
            return
        found = await self._uow.workspace_members.list_in_workspace(workspace_id, user_ids)
        if {m.user_id for m in found} != user_ids:
            raise AssigneeNotInWorkspaceError

    async def create(self, payload: list[TaskCreate], workspace_id: UUID) -> list[TaskRead]:
        """Create a task in the workspace after validating the optional assignee."""
        user_ids = set[UUID]()
        fields = []
        for p in payload:
            if p.assigned_user_id is not None:
                user_ids.add(p.assigned_user_id)
            fields.append(
                TaskCreateData(**p.model_dump(), workspace_id=workspace_id)
            )
        await self._assert_assignees_in_workspace(workspace_id, user_ids)

        tasks = await self._uow.tasks.create_many(fields)
        log_event(
            logger,
            INFO,
            TASKS_CREATED,
            after_commit=self._uow,
            count=len(tasks),
            workspace_id=workspace_id,
            actor_id=current_user_id_ctx.get(),
        )
        await invalidate_summary_cache(workspace_id)
        return [self._to_read(task) for task in tasks]

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
            uid = updates["assigned_user_id"]
            await self._assert_assignees_in_workspace(
                workspace_id, {uid} if uid is not None else set()
            )

        task = await self._uow.tasks.update(
            workspace_id,
            task_id,
            TaskUpdateData(**updates),
        )
        if task is None:
            raise TaskNotFoundError

        log_event(
            logger,
            INFO,
            TASK_UPDATED,
            after_commit=self._uow,
            workspace_id=workspace_id,
            task_id=task_id,
            actor_id=current_user_id_ctx.get(),
        )
        await invalidate_summary_cache(workspace_id)
        return self._to_read(task)

    async def delete(self, workspace_id: UUID, task_ids: list[UUID]) -> None:
        """Delete a task in the workspace."""
        requested = set(task_ids)
        deleted = await self._uow.tasks.delete_many(workspace_id, requested)
        log_event(
            logger,
            INFO,
            TASKS_DELETED,
            after_commit=self._uow,
            count=deleted,
            requested=len(requested),
            workspace_id=workspace_id,
            actor_id=current_user_id_ctx.get(),
        )
        await invalidate_summary_cache(workspace_id)

    async def summary(self, workspace_id: UUID) -> TaskSummaryRead:
        cached = await get_cached_summary(workspace_id)
        if cached is not None:
            try:
                return TaskSummaryRead.model_validate(cached)
            except ValidationError:
                log_event(
                    logger,
                    ERROR,
                    CACHE_BACKEND_ERROR,
                    exc_info=True,
                    op="get",
                    key="invalid_cached_summary",
                    workspace_id=workspace_id,
                )

        status_count = await self._uow.tasks.count_by_status(workspace_id)
        summary = TaskSummaryRead(
            workspace_id=workspace_id,
            total=sum(status_count.values()),
            **status_count,
        )

        await set_cached_summary(
            workspace_id,
            {**summary.model_dump(mode="json"), "workspace_id": str(workspace_id)},
        )
        return summary

    async def export(self, workspace_id: UUID, to_email: str) -> None:
        actor_id = current_user_id_ctx.get()
        try:
            export_workspace_tasks.delay(str(workspace_id), to_email, actor_id)
        except OperationalError:
            raise ServiceUnavailableError
