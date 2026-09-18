"""Workspace persistence."""

from datetime import datetime
from uuid import UUID

from pydantic import UUID4, BaseModel, ConfigDict

from app.models import Workspace
from app.repositories.base import BaseRepository


class WorkspaceRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    name: str
    created_at: datetime


class WorkspaceRepository(BaseRepository):
    async def create(self, name: str) -> WorkspaceRecord:
        """Insert a workspace and return the persisted record."""
        workspace = Workspace(name=name)
        await self.add_flush_refresh(workspace)
        return self.to_record(WorkspaceRecord, workspace)

    async def get(self, workspace_id: UUID) -> WorkspaceRecord | None:
        """Fetch a workspace by id, or None."""
        workspace = await self._session.get(Workspace, workspace_id)
        if workspace is None:
            return None
        return self.to_record(WorkspaceRecord, workspace)
