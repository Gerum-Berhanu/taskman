"""Workspace application services."""

import logging
from uuid import UUID

from app.core.exceptions import WorkspaceForbiddenError
from app.dto.repository import WorkspaceCreateData, WorkspaceRecord
from app.repositories.unit_of_work import UnitOfWork
from app.dto.api.workspace import WorkspaceCreate, WorkspaceRead
from app.dto.api.workspace_member import WorkspaceMemberCreate, WorkspaceMemberRole
from app.observability.events import DomainLogEvent
from app.services.workspace_member import WorkspaceMemberService


logger = logging.getLogger(__name__)


class WorkspaceService:
    """Create and fetch workspaces."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow
        self._member_service = WorkspaceMemberService(uow)

    @staticmethod
    def _to_read(record: WorkspaceRecord) -> WorkspaceRead:
        return WorkspaceRead.model_validate(record, from_attributes=True)

    async def create(self, payload: WorkspaceCreate, user_id: UUID) -> WorkspaceRead:
        """Create a workspace and add the creating user as owner."""
        workspace = await self._uow.workspaces.create(
            WorkspaceCreateData(name=payload.name)
        )
        await self._member_service.create(
            workspace.id,
            WorkspaceMemberCreate(
                user_id=user_id,
                role=WorkspaceMemberRole.OWNER,
            ),
        )
        workspace_id = workspace.id
        self._uow.after_commit(
            lambda: logger.info(
                "%s workspace_id=%s owner_id=%s",
                DomainLogEvent.WORKSPACE_CREATED,
                workspace_id,
                user_id,
            )
        )
        return self._to_read(workspace)

    async def get(self, workspace_id: UUID) -> WorkspaceRead:
        """Return a workspace or raise forbidden (no existence leak)."""
        workspace = await self._uow.workspaces.get(workspace_id)
        if workspace is None:
            raise WorkspaceForbiddenError
        return self._to_read(workspace)

    async def list_by_user(self, user_id: UUID) -> list[WorkspaceRead]:
        """Return a list of workspaces that the provided user is a member of."""
        memberships = await self._uow.workspace_members.list_user_memberships(user_id)
        if not memberships:
            raise WorkspaceForbiddenError

        workspace_ids = {membership.workspace_id for membership in memberships}
        workspaces = await self._uow.workspaces.list_all(workspace_ids)
        return [self._to_read(workspace) for workspace in workspaces]
