from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    MembershipAlreadyExistsError,
    UserNotFoundError,
    WorkspaceForbiddenError,
)
from app.database.unit_of_work import UnitOfWork
from app.repositories.workspace_member import (
    WorkspaceMemberCreateData,
    WorkspaceMemberRecord,
)
from app.schemas.workspace_member import WorkspaceMemberCreate, WorkspaceMemberRole


class WorkspaceMemberService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def create(
        self, workspace_id: UUID, new_membership: WorkspaceMemberCreate
    ) -> WorkspaceMemberRecord:
        workspace = await self._uow.workspaces.get(workspace_id)
        if workspace is None:
            # Same as non-member: do not reveal whether the workspace exists.
            raise WorkspaceForbiddenError

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

    async def get(
        self, workspace_id: UUID, user_id: UUID
    ) -> WorkspaceMemberRecord | None:
        return await self._uow.workspace_members.get(workspace_id, user_id)

    async def get_role(
        self, workspace_id: UUID, user_id: UUID
    ) -> WorkspaceMemberRole:
        # Missing workspace and non-membership must be indistinguishable.
        member = await self._uow.workspace_members.get(workspace_id, user_id)
        if member is None:
            raise WorkspaceForbiddenError
        return WorkspaceMemberRole(member.role)
