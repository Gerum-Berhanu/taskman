"""User persistence."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.user import User


class UserRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    hashed_password: str
    is_active: bool
    created_at: datetime


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> UserRecord | None:
        statement = select(User).where(User.email == email)
        result = await self._session.exec(statement)
        user = result.first()
        if user is None:
            return None
        return UserRecord.model_validate(user)

    async def get_by_id(self, user_id: UUID) -> UserRecord | None:
        user = await self._session.get(User, user_id)
        if user is None:
            return None
        return UserRecord.model_validate(user)

    async def create(self, *, email: str, hashed_password: str) -> UserRecord:
        user = User(email=email, hashed_password=hashed_password)
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return UserRecord.model_validate(user)

    async def set_is_active(
        self, user_id: UUID, *, is_active: bool
    ) -> UserRecord | None:
        user = await self._session.get(User, user_id)
        if user is None:
            return None
        user.is_active = is_active
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return UserRecord.model_validate(user)
