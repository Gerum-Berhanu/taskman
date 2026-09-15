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


class MemberBase(BaseModel):
    workspace_id: UUID4
    user_id: UUID4
    role: str


class WorkspaceMemberRecord(MemberBase):
    model_config = ConfigDict(from_attributes=True)

    joined_at: datetime


class MemberCreateData(MemberBase):
    pass


class WorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_workspace(self, workspace_name: str) -> WorkspaceRecord:
        workspace = Workspace(name=workspace_name)
        await add_flush_refresh(self._session, workspace)
        return to_record(WorkspaceRecord, workspace)

    async def create_membership(self, fields: MemberCreateData) -> WorkspaceMemberRecord:
        membership = WorkspaceMember(**fields.model_dump())
        await add_flush_refresh(self._session, membership)
        return to_record(WorkspaceMemberRecord, membership)

    async def get_workspace(self, workspace_id: UUID) -> WorkspaceRecord | None:
        space = await self._session.get(Workspace, workspace_id)
        if space is None:
            return None
        return to_record(WorkspaceRecord, space)

    async def get_membership(
        self, workspace_id: UUID, user_id: UUID
    ) -> WorkspaceMemberRecord | None:
        member = await self._session.get(WorkspaceMember, (workspace_id, user_id))
        if member is None:
            return None
        return to_record(WorkspaceMemberRecord, member)
