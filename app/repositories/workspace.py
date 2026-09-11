from datetime import datetime
from uuid import UUID

from pydantic import UUID4, BaseModel, ConfigDict
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Workspace, WorkspaceMember


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


def _to_space_record(space: Workspace) -> WorkspaceRecord:
    return WorkspaceRecord.model_validate(space)


def _to_member_record(member: WorkspaceMember) -> WorkspaceMemberRecord:
    return WorkspaceMemberRecord.model_validate(member)


class WorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_workspace(self, workspace_name: str) -> WorkspaceRecord:
        workspace = Workspace(name=workspace_name)
        self._session.add(workspace)
        await self._session.flush()
        await self._session.refresh(workspace)
        return _to_space_record(workspace)

    async def create_membership(self, fields: MemberCreateData) -> WorkspaceMemberRecord:
        membership = WorkspaceMember(**fields.model_dump())
        self._session.add(membership)
        await self._session.flush()
        await self._session.refresh(membership)
        return _to_member_record(membership)

    async def get_workspace(self, workspace_id: UUID) -> WorkspaceRecord | None:
        space = await self._session.get(Workspace, workspace_id)
        if space is None:
            return None
        return _to_space_record(space)

    async def get_membership(
        self, workspace_id: UUID, user_id: UUID
    ) -> WorkspaceMemberRecord | None:
        member = await self._session.get(WorkspaceMember, (workspace_id, user_id))
        if member is None:
            return None
        return _to_member_record(member)
