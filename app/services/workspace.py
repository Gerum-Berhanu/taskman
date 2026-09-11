from uuid import UUID
from app.core.exceptions import MembershipTargetNotFound
from app.database.unit_of_work import UnitOfWork
from app.repositories import WorkspaceRecord
from app.repositories.workspace import MemberCreateData, WorkspaceMemberRecord
from app.schemas.workspace import WorkspaceCreate, WorkspaceMemberCreate, WorkspaceMemberRole


class WorkspaceService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def create_workspace(self, data: WorkspaceCreate, user_id: UUID) -> WorkspaceRecord:
        space = await self._uow.workspaces.create_workspace(data.name)
        member = WorkspaceMemberCreate(
            user_id=user_id,
            role=WorkspaceMemberRole.OWNER
        )
        await self.create_membership(space.id, member)
        return space

    async def create_membership(
        self, workspace_id: UUID, new_membership: WorkspaceMemberCreate
    ) -> WorkspaceMemberRecord:
        fields = MemberCreateData(
            workspace_id=workspace_id,
            user_id=new_membership.user_id,
            role=new_membership.role.value
        )
        membership = await self._uow.workspaces.create_membership(fields)
        if membership is None:
            raise MembershipTargetNotFound
        return membership
        