from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel

class RefreshToken(SQLModel, table=True):
    __tablename__: str = "refresh_tokens"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    client_session_id: UUID = Field(foreign_key="client_sessions.id", index=True)
    token_hash: str = Field(unique=True)
