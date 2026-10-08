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


class WorkspaceRepository(BaseRepository):
    async def create(self, fields: WorkspaceCreateData) -> WorkspaceRecord:
        """Insert a workspace and return the persisted record."""
        workspace = Workspace(**fields.model_dump())
        await self.add_flush_refresh(workspace)
        return self.to_record(workspace)

    async def get(self, workspace_id: UUID) -> WorkspaceRecord | None:
        """Fetch a workspace by id, or None."""
        workspace = await self._session.get(Workspace, workspace_id)
        if workspace is None:
            return None
        return self.to_record(workspace)

    async def list_all(self, workspace_ids: set[UUID]) -> list[WorkspaceRecord]:
        """List all workspaces for the provided Ids"""
        statement = select(Workspace).where(col(Workspace.id).in_(workspace_ids))
        result = await self._session.exec(statement)
        return [self.to_record(workspace) for workspace in result.all()]
