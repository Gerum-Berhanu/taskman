import logging
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    MembershipAlreadyExistsError,
    UserNotFoundError,
    WorkspaceForbiddenError,
)
from app.core.request_context import current_user_id_ctx
from app.database.unit_of_work import UnitOfWork
from app.repositories.workspace_member import (
    WorkspaceMemberCreateData,
    WorkspaceMemberRecord,
)
from app.schemas.workspace_member import WorkspaceMemberCreate, WorkspaceMemberRole


logger = logging.getLogger(__name__)


class WorkspaceMemberService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def create(
        self, workspace_id: UUID, new_membership: WorkspaceMemberCreate
    ) -> WorkspaceMemberRecord:
        """Add a member; missing workspace looks like forbidden (no enumeration)."""
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
            created = await self._uow.workspace_members.create(fields)
        except IntegrityError:
            raise MembershipAlreadyExistsError from None

        member_id, role = created.user_id, created.role
        actor_id = current_user_id_ctx.get()
        self._uow.after_commit(
            lambda: logger.info(
                "workspace_member_added workspace_id=%s member_id=%s role=%s actor_id=%s",
                workspace_id,
                member_id,
                role,
                actor_id,
            )
        )
        return created

    async def get(
        self, workspace_id: UUID, user_id: UUID
    ) -> WorkspaceMemberRecord | None:
        """Return a membership row if present."""
        return await self._uow.workspace_members.get(workspace_id, user_id)

    async def get_role(
        self, workspace_id: UUID, user_id: UUID
    ) -> WorkspaceMemberRole:
        """Return the user's role; missing workspace and non-member are both forbidden."""
        # Missing workspace and non-membership must be indistinguishable.
        member = await self._uow.workspace_members.get(workspace_id, user_id)
        if member is None:
            raise WorkspaceForbiddenError
        return WorkspaceMemberRole(member.role)
