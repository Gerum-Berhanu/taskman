from uuid import UUID
from sqlmodel import Field

from app.models.base import BaseTable

class RefreshToken(BaseTable, table=True):
    __tablename__: str = "refresh_tokens"

    client_session_id: UUID = Field(foreign_key="client_sessions.id", ondelete="CASCADE", index=True)
    token_hash: str = Field(unique=True)
