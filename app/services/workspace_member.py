"""Workspace membership application services."""

import logging
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    MembershipAlreadyExistsError,
    UserNotFoundError,
    WorkspaceForbiddenError,
)
from app.core.request_context import current_user_id_ctx
from app.dto.repository import WorkspaceMemberCreateData, WorkspaceMemberRecord
from app.repositories.unit_of_work import UnitOfWork
from app.dto.api.workspace_member import (
    WorkspaceMemberCreate,
    WorkspaceMemberRead,
    WorkspaceMemberRole,
)


logger = logging.getLogger(__name__)


class WorkspaceMemberService:
    """Add members and resolve roles within a workspace."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    @staticmethod
    def _to_read(record: WorkspaceMemberRecord) -> WorkspaceMemberRead:
        return WorkspaceMemberRead.model_validate(record, from_attributes=True)

    async def create(
        self, workspace_id: UUID, payload: WorkspaceMemberCreate
    ) -> WorkspaceMemberRead:
        """Add a member; missing workspace looks like forbidden (no enumeration)."""
        workspace = await self._uow.workspaces.get(workspace_id)
        if workspace is None:
            # Same as non-member: do not reveal whether the workspace exists.
            raise WorkspaceForbiddenError

        user = await self._uow.users.get(payload.user_id)
        if user is None:
            raise UserNotFoundError

        membership = await self._uow.workspace_members.get(workspace_id, user.id)
        if membership is not None:
            raise MembershipAlreadyExistsError

        fields = WorkspaceMemberCreateData(
            workspace_id=workspace_id,
            user_id=payload.user_id,
            role=payload.role.value,
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
        return self._to_read(created)

    async def get(
        self, workspace_id: UUID, user_id: UUID
    ) -> WorkspaceMemberRead | None:
        """Return a membership if present."""
        membership = await self._uow.workspace_members.get(workspace_id, user_id)
        if membership is None:
            return None
        return self._to_read(membership)

    async def get_role(
        self, workspace_id: UUID, user_id: UUID
    ) -> WorkspaceMemberRole:
        """Return the user's role; missing workspace and non-member are both forbidden."""
        # Missing workspace and non-membership must be indistinguishable.
        membership = await self._uow.workspace_members.get(workspace_id, user_id)
        if membership is None:
            raise WorkspaceForbiddenError
        return WorkspaceMemberRole(membership.role)
