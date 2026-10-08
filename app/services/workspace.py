"""Workspace application services."""

import logging
from uuid import UUID

from app.core.exceptions import WorkspaceForbiddenError
from app.repositories.unit_of_work import UnitOfWork
from app.repositories import WorkspaceRecord
from app.repositories.workspace import WorkspaceCreateData
from app.schemas.workspace import WorkspaceCreate
from app.schemas.workspace_member import WorkspaceMemberCreate, WorkspaceMemberRole
from app.services.workspace_member import WorkspaceMemberService


logger = logging.getLogger(__name__)


class WorkspaceService:
    """Create and fetch workspaces."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow
        self._members = WorkspaceMemberService(uow)

    async def create(self, data: WorkspaceCreate, user_id: UUID) -> WorkspaceRecord:
        """Create a workspace and add the creating user as owner."""
        workspace = await self._uow.workspaces.create(
            WorkspaceCreateData(name=data.name)
        )
        await self._members.create(
            workspace.id,
            WorkspaceMemberCreate(
                user_id=user_id,
                role=WorkspaceMemberRole.OWNER,
            ),
        )
        workspace_id = workspace.id
        self._uow.after_commit(
            lambda: logger.info(
                "workspace_created workspace_id=%s owner_id=%s",
                workspace_id,
                user_id,
            )
        )
        return workspace

    async def get(self, workspace_id: UUID) -> WorkspaceRecord:
        """Return a workspace or raise forbidden (no existence leak)."""
        workspace = await self._uow.workspaces.get(workspace_id)
        if workspace is None:
            raise WorkspaceForbiddenError
        return workspace

    async def list_by_user(self, user_id: UUID) -> list[WorkspaceRecord]:
        """Return a list of workspaces that the provided user is a member of"""
        members = await self._uow.workspace_members.list_user_memberships(user_id)
        if not members:
            raise WorkspaceForbiddenError
        
        workspace_ids = {member.workspace_id for member in members}
        workspaces = await self._uow.workspaces.list_all(workspace_ids)
        return workspaces
