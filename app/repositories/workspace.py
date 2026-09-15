"""Workspace and membership persistence."""

from datetime import datetime
from uuid import UUID

from pydantic import UUID4, BaseModel, ConfigDict
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Workspace, WorkspaceMember
from app.repositories._persistence import add_flush_refresh, to_record


class WorkspaceRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    name: str
    created_at: datetime


class WorkspaceMemberBase(BaseModel):
    workspace_id: UUID4
    user_id: UUID4
    role: str


class WorkspaceMemberRecord(WorkspaceMemberBase):
    model_config = ConfigDict(from_attributes=True)

    joined_at: datetime


class WorkspaceMemberCreateData(WorkspaceMemberBase):
    pass


class WorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, name: str) -> WorkspaceRecord:
        workspace = Workspace(name=name)
        await add_flush_refresh(self._session, workspace)
        return to_record(WorkspaceRecord, workspace)

    async def get(self, workspace_id: UUID) -> WorkspaceRecord | None:
        workspace = await self._session.get(Workspace, workspace_id)
        if workspace is None:
            return None
        return to_record(WorkspaceRecord, workspace)

    # Prefixed until membership moves to its own repository (slice 9).
    async def create_membership(
        self, fields: WorkspaceMemberCreateData
    ) -> WorkspaceMemberRecord:
        membership = WorkspaceMember(**fields.model_dump())
        await add_flush_refresh(self._session, membership)
        return to_record(WorkspaceMemberRecord, membership)

    async def get_membership(
        self, workspace_id: UUID, user_id: UUID
    ) -> WorkspaceMemberRecord | None:
        member = await self._session.get(WorkspaceMember, (workspace_id, user_id))
        if member is None:
            return None
        return to_record(WorkspaceMemberRecord, member)
