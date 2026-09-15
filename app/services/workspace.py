from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    MembershipAlreadyExistsError,
    UserNotFoundError,
    WorkspaceForbiddenError,
    WorkspaceNotFoundError,
)
from app.database.unit_of_work import UnitOfWork
from app.repositories import WorkspaceRecord
from app.repositories.workspace_member import (
    WorkspaceMemberCreateData,
    WorkspaceMemberRecord,
)
from app.schemas.workspace import WorkspaceCreate, WorkspaceMemberCreate, WorkspaceMemberRole


class WorkspaceService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def create_workspace(
        self, data: WorkspaceCreate, user_id: UUID
    ) -> WorkspaceRecord:
        workspace = await self._uow.workspaces.create(data.name)
        member = WorkspaceMemberCreate(
            user_id=user_id,
            role=WorkspaceMemberRole.OWNER,
        )
        await self.create_membership(workspace.id, member)
        return workspace

    async def create_membership(
        self, workspace_id: UUID, new_membership: WorkspaceMemberCreate
    ) -> WorkspaceMemberRecord:
        await self.get_workspace(workspace_id)

        user = await self._uow.users.get_by_id(new_membership.user_id)
        if user is None:
            raise UserNotFoundError

        member = await self._uow.workspace_members.get(workspace_id, user.id)
        if member is not None:
            raise MembershipAlreadyExistsError

        fields = WorkspaceMemberCreateData(
            workspace_id=workspace_id,
            user_id=new_membership.user_id,
            role=new_membership.role.value,
        )
        try:
            return await self._uow.workspace_members.create(fields)
        except IntegrityError:
            raise MembershipAlreadyExistsError from None

    async def get_workspace(self, workspace_id: UUID) -> WorkspaceRecord:
        workspace = await self._uow.workspaces.get(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError
        return workspace

    async def get_role(self, workspace_id: UUID, user_id: UUID) -> WorkspaceMemberRole:
        await self.get_workspace(workspace_id)
        member = await self._uow.workspace_members.get(workspace_id, user_id)
        if member is None:
            raise WorkspaceForbiddenError
        return WorkspaceMemberRole(member.role)
