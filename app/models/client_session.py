from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlmodel import Field
from app.core.config import settings
from app.core.timeutils import utcnow
from app.models.base import BaseTable


class ClientSession(BaseTable, table=True):
    __tablename__: str = "client_sessions"

    user_id: UUID = Field(foreign_key="users.id", ondelete="CASCADE", index=True)
    active_token_id: UUID | None = Field(
        default=None, foreign_key="refresh_tokens.id", ondelete="SET NULL", unique=True
    )
    revoked_at: datetime | None = None
    rotated_at: datetime | None = Field(default=None)
    expires_at: datetime = Field(
        default_factory=lambda: utcnow()
            + timedelta(minutes=settings.refresh_token_expire_minutes)
    )
