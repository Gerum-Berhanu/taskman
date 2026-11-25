"""Workspace membership persistence."""

from collections.abc import Collection
from uuid import UUID

from sqlmodel import col, select

from app.models import WorkspaceMember
from app.repositories.base import BaseRepository
from app.dto.repository import WorkspaceMemberCreateData, WorkspaceMemberRecord


class WorkspaceMemberRepository(
    BaseRepository[WorkspaceMember, WorkspaceMemberRecord, WorkspaceMemberCreateData]
):
    model = WorkspaceMember
    record = WorkspaceMemberRecord

    async def list_user_memberships(self, user_id: UUID) -> list[WorkspaceMemberRecord]:
        statement = select(WorkspaceMember).where(WorkspaceMember.user_id == user_id)
        result = await self._session.exec(statement)
        return [self._to_record(membership) for membership in result.all()]

    async def list_in_workspace(
        self, workspace_id: UUID, user_ids: Collection[UUID]
    ) -> list[WorkspaceMemberRecord]:
        if not user_ids:
            return []
        statement = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            col(WorkspaceMember.user_id).in_(user_ids)
        )
        result = await self._session.exec(statement)
        return [self._to_record(membership) for membership in result.all()]
