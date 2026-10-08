"""Workspace membership persistence."""

from datetime import datetime
from uuid import UUID

from pydantic import UUID4, BaseModel, ConfigDict
from sqlmodel import select

from app.models import WorkspaceMember
from app.repositories.base import BaseRepository


class WorkspaceMemberRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workspace_id: UUID4
    user_id: UUID4
    role: str
    joined_at: datetime


class WorkspaceMemberCreateData(BaseModel):
    workspace_id: UUID4
    user_id: UUID4
    role: str


class WorkspaceMemberRepository(BaseRepository):
    async def create(self, fields: WorkspaceMemberCreateData) -> WorkspaceMemberRecord:
        """Insert a membership and return the persisted record."""
        membership = WorkspaceMember(**fields.model_dump())
        await self.add_flush_refresh(membership)
        return self.to_record(membership)

    async def get(
        self, workspace_id: UUID, user_id: UUID
    ) -> WorkspaceMemberRecord | None:
        """Fetch membership by composite key, or None."""
        member = await self._session.get(WorkspaceMember, (workspace_id, user_id))
        if member is None:
            return None
        return self.to_record(member)

    async def list_user_memberships(self, user_id: UUID) -> list[WorkspaceMemberRecord]:
        statement = select(WorkspaceMember).where(WorkspaceMember.user_id == user_id)
        result = await self._session.exec(statement)
        return [self.to_record(member) for member in result.all()]
