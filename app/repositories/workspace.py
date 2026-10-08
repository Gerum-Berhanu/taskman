"""Workspace persistence."""

from uuid import UUID

from sqlmodel import col, select

from app.models import Workspace
from app.repositories.base import BaseRepository
from app.dto.repository import WorkspaceCreateData, WorkspaceRecord


class WorkspaceRepository(BaseRepository[Workspace, WorkspaceRecord, WorkspaceCreateData]):
    model = Workspace
    record = WorkspaceRecord

    async def list_all(self, workspace_ids: set[UUID]) -> list[WorkspaceRecord]:
        """List all workspaces for the provided Ids."""
        statement = select(Workspace).where(col(Workspace.id).in_(workspace_ids))
        result = await self._session.exec(statement)
        return [self._to_record(workspace) for workspace in result.all()]
