from uuid import UUID

from app.core.exceptions import WorkspaceNotFoundError
from app.database.unit_of_work import UnitOfWork
from app.repositories import WorkspaceRecord
from app.schemas.workspace import WorkspaceCreate, WorkspaceMemberCreate, WorkspaceMemberRole
from app.services.workspace_member import WorkspaceMemberService


class WorkspaceService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow
        self._members = WorkspaceMemberService(uow)

    async def create(self, data: WorkspaceCreate, user_id: UUID) -> WorkspaceRecord:
        workspace = await self._uow.workspaces.create(data.name)
        await self._members.create(
            workspace.id,
            WorkspaceMemberCreate(
                user_id=user_id,
                role=WorkspaceMemberRole.OWNER,
            ),
        )
        return workspace

    async def get(self, workspace_id: UUID) -> WorkspaceRecord:
        workspace = await self._uow.workspaces.get(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError
        return workspace
