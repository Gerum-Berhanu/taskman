from datetime import datetime
from uuid import UUID
from pydantic import UUID4, BaseModel, ConfigDict
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import User, Workspace, WorkspaceMember


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

    async def create_membership(self, fields: MemberCreateData) -> WorkspaceMemberRecord | None:
        workspace = await self._session.get(Workspace, fields.workspace_id)
        if workspace is None:
            return None

        user = await self._session.get(User, fields.user_id)
        if user is None:
            return None

        membership = WorkspaceMember(**fields.model_dump())
        self._session.add(membership)
        await self._session.flush()
        await self._session.refresh(membership)
        return _to_member_record(membership)
        