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


class WorkspaceMemberRepository(
    BaseRepository[WorkspaceMember, WorkspaceMemberRecord, WorkspaceMemberCreateData]
):
    model = WorkspaceMember
    record = WorkspaceMemberRecord

    async def list_user_memberships(self, user_id: UUID) -> list[WorkspaceMemberRecord]:
        statement = select(WorkspaceMember).where(WorkspaceMember.user_id == user_id)
        result = await self._session.exec(statement)
        return [self._to_record(member) for member in result.all()]
