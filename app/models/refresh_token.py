from datetime import datetime, timedelta
from uuid import UUID
from sqlmodel import JSON, Column, Field

from app.core.config import settings
from app.core.timeutils import utcnow
from app.models.base import BaseTable


class UserSession(BaseTable, table=True):
    __tablename__: str = "user_sessions"

    user_id: UUID = Field(foreign_key="users.id", index=True)
    active_token_hash: str = Field(unique=True)
    used_token_hashes: list[dict[str, str]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False)
    )
    is_revoked: bool = Field(default=False)
    expires_at: datetime = Field(
        default_factory=lambda: utcnow() 
        + timedelta(minutes=settings.refresh_token_expire_minutes)
    )