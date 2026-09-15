"""User persistence."""

from datetime import datetime
from uuid import UUID

from pydantic import UUID4, BaseModel, ConfigDict, EmailStr
from sqlmodel import select

from app.models.user import User
from app.repositories._persistence import add_flush_refresh, to_record
from app.repositories.base import BaseRepository


class UserRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    email: EmailStr
    hashed_password: str
    is_active: bool
    created_at: datetime


class UserCreateData(BaseModel):
    email: EmailStr
    hashed_password: str


class UserRepository(BaseRepository):
    async def get_by_email(self, email: str) -> UserRecord | None:
        statement = select(User).where(User.email == email)
        result = await self._session.exec(statement)
        user = result.first()
        if user is None:
            return None
        return to_record(UserRecord, user)

    async def get_by_id(self, user_id: UUID) -> UserRecord | None:
        user = await self._session.get(User, user_id)
        if user is None:
            return None
        return to_record(UserRecord, user)

    async def create(self, fields: UserCreateData) -> UserRecord:
        user = User(**fields.model_dump())
        await add_flush_refresh(self._session, user)
        return to_record(UserRecord, user)

    async def set_is_active(
        self, user_id: UUID, *, is_active: bool
    ) -> UserRecord | None:
        user = await self._session.get(User, user_id)
        if user is None:
            return None
        user.is_active = is_active
        await add_flush_refresh(self._session, user)
        return to_record(UserRecord, user)
