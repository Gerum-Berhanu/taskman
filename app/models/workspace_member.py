from datetime import datetime
from uuid import UUID
from sqlmodel import Field, SQLModel

from app.core.timeutils import utcnow


class WorkspaceMember(SQLModel, table=True):
    __tablename__: str = "workspace_members"

    workspace_id: UUID = Field(primary_key=True, foreign_key="workspaces.id", ondelete="CASCADE")
    user_id: UUID = Field(primary_key=True, foreign_key="users.id", ondelete="CASCADE", index=True)
    role: str = Field()
    joined_at: datetime = Field(default_factory=utcnow)
    