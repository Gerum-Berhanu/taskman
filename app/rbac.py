from typing import Annotated

from fastapi import Path
from pydantic import UUID4
from app.core.exceptions import WorkspaceForbiddenError
from app.deps import CurrentUserDep, WorkspaceServiceDep
from app.schemas.workspace import WorkspaceMemberRole


_ROLE_RANK: dict[WorkspaceMemberRole, int] = {
    WorkspaceMemberRole.VIEWER: 1,
    WorkspaceMemberRole.EDITOR: 2,
    WorkspaceMemberRole.OWNER: 3,
}


def role_at_least(actual: WorkspaceMemberRole, required: WorkspaceMemberRole) -> bool:
    return _ROLE_RANK[actual] >= _ROLE_RANK[required]


class RequireRole:
    def __init__(self, minimum: WorkspaceMemberRole) -> None:
        self.minimum = minimum
    async def __call__(
        self,
        workspace_id: Annotated[UUID4, Path()],
        current_user: CurrentUserDep,
        workspace_service: WorkspaceServiceDep,
    ) -> None:
        role = await workspace_service.get_role(workspace_id, current_user.id)
        if not role_at_least(role, self.minimum):
            raise WorkspaceForbiddenError
    