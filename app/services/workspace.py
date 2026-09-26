import logging
from uuid import UUID

from app.core.exceptions import WorkspaceForbiddenError
from app.database.unit_of_work import UnitOfWork
from app.repositories import WorkspaceRecord
from app.schemas.workspace import WorkspaceCreate
from app.schemas.workspace_member import WorkspaceMemberCreate, WorkspaceMemberRole
from app.services.workspace_member import WorkspaceMemberService


logger = logging.getLogger(__name__)


class WorkspaceService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow
        self._members = WorkspaceMemberService(uow)

    async def create(self, data: WorkspaceCreate, user_id: UUID) -> WorkspaceRecord:
        """Create a workspace and add the creating user as owner."""
        workspace = await self._uow.workspaces.create(data.name)
        await self._members.create(
            workspace.id,
            WorkspaceMemberCreate(
                user_id=user_id,
                role=WorkspaceMemberRole.OWNER,
            ),
        )
        logger.info(
            "workspace_created workspace_id=%s owner_id=%s",
            workspace.id,
            user_id,
        )
        return workspace

    async def get(self, workspace_id: UUID) -> WorkspaceRecord:
        """Return a workspace or raise forbidden (no existence leak)."""
        workspace = await self._uow.workspaces.get(workspace_id)
        if workspace is None:
            raise WorkspaceForbiddenError
        return workspace
