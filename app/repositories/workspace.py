"""Workspace persistence."""

from datetime import datetime
from uuid import UUID

from pydantic import UUID4, BaseModel, ConfigDict
from sqlmodel import col, select

from app.models import Workspace
from app.repositories.base import BaseRepository


class WorkspaceRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    name: str
    created_at: datetime


class WorkspaceCreateData(BaseModel):
    name: str


class WorkspaceRepository(
    BaseRepository[Workspace, WorkspaceRecord, WorkspaceCreateData]
):
    model = Workspace
    record = WorkspaceRecord

    async def list_all(self, workspace_ids: set[UUID]) -> list[WorkspaceRecord]:
        """List all workspaces for the provided Ids"""
        statement = select(Workspace).where(col(Workspace.id).in_(workspace_ids))
        result = await self._session.exec(statement)
        return [self._to_record(workspace) for workspace in result.all()]
