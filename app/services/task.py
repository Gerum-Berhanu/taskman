from uuid import UUID

from app.core.exceptions import (
    AssigneeNotInWorkspaceError,
    TaskNotFoundError,
    UserNotFoundError,
)
from app.database.unit_of_work import UnitOfWork
from app.repositories.task import TaskCreateData, TaskRecord, TaskUpdateData
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def _validate_assignee(
        self, workspace_id: UUID, assigned_user_id: UUID | None
    ) -> None:
        if assigned_user_id is None:
            return
        if await self._uow.users.get_by_id(assigned_user_id) is None:
            raise UserNotFoundError
        member = await self._uow.workspaces.get_membership(
            workspace_id, assigned_user_id
        )
        if member is None:
            raise AssigneeNotInWorkspaceError

    async def create(self, data: TaskCreate, workspace_id: UUID) -> TaskRecord:
        await self._validate_assignee(workspace_id, data.assigned_user_id)
        fields = TaskCreateData(**data.model_dump(), workspace_id=workspace_id)
        return await self._uow.tasks.create(fields=fields)

    async def get(self, workspace_id: UUID, task_id: UUID) -> TaskRecord:
        task = await self._uow.tasks.get(workspace_id, task_id)
        if not task:
            raise TaskNotFoundError
        return task

    async def list_all(self, workspace_id: UUID) -> list[TaskRecord]:
        return await self._uow.tasks.list_all(workspace_id)

    async def update(
        self, task_id: UUID, workspace_id: UUID, data: TaskUpdate
    ) -> TaskRecord:
        updates = data.model_dump(exclude_unset=True)
        if "assigned_user_id" in updates:
            await self._validate_assignee(workspace_id, updates["assigned_user_id"])

        task = await self._uow.tasks.update(
            task_id,
            workspace_id,
            TaskUpdateData(**updates),
        )
        if task is None:
            raise TaskNotFoundError
        return task

    async def delete(self, task_id: UUID, workspace_id: UUID) -> None:
        if not await self._uow.tasks.delete(task_id, workspace_id):
            raise TaskNotFoundError
