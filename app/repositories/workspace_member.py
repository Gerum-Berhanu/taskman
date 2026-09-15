"""Workspace membership persistence."""

from datetime import datetime
from uuid import UUID

from pydantic import UUID4, BaseModel, ConfigDict

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
        membership = WorkspaceMember(**fields.model_dump())
        await self.add_flush_refresh(membership)
        return self.to_record(WorkspaceMemberRecord, membership)

    async def get(
        self, workspace_id: UUID, user_id: UUID
    ) -> WorkspaceMemberRecord | None:
        member = await self._session.get(WorkspaceMember, (workspace_id, user_id))
        if member is None:
            return None
        return self.to_record(WorkspaceMemberRecord, member)
