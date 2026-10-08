"""User persistence."""

from uuid import UUID

from sqlmodel import select

from app.models.user import User
from app.repositories.base import BaseRepository
from app.dto.repository import UserCreateData, UserRecord


class UserRepository(BaseRepository[User, UserRecord, UserCreateData]):
    model = User
    record = UserRecord

    async def get_by_email(self, email: str) -> UserRecord | None:
        """Fetch a user by email, or None."""
        statement = select(User).where(User.email == email)
        result = await self._session.exec(statement)
        user = result.first()
        if user is None:
            return None
        return self._to_record(user)

    async def set_is_active(
        self, user_id: UUID, *, is_active: bool
    ) -> UserRecord | None:
        """Update is_active for a user; return None if missing."""
        user = await self._session.get(User, user_id)
        if user is None:
            return None
        user.is_active = is_active
        await self._flush_refresh(user)
        return self._to_record(user)
