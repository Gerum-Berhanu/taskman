"""User repository: protocol, in-memory, and SQL implementations."""

from typing import Protocol
from uuid import UUID, uuid4
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core import timeutils as tu
from app.database.models import User
from app.repositories.records import UserRecord


class UserRepository(Protocol):
    async def get_by_email(self, email: str) -> UserRecord | None: ...

    async def create(self, *, email: str, hashed_password: str) -> UserRecord: ...


def _to_user_record(user: User) -> UserRecord:
    return UserRecord(
        id=user.id,
        email=user.email,
        hashed_password=user.hashed_password,
        is_active=user.is_active,
        created_at=user.created_at,
    )


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self._users: dict[UUID, UserRecord] = {}

    async def get_by_email(self, email: str) -> UserRecord | None:
        for user in self._users.values():
            if user["email"] == email:
                return user
        return None

    async def create(self, *, email: str, hashed_password: str) -> UserRecord:
        user_id = uuid4()
        user: UserRecord = {
            "id": user_id,
            "email": email,
            "hashed_password": hashed_password,
            "is_active": True,
            "created_at": tu.utcnow(),
        }
        self._users[user_id] = user
        return user


class SqlUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> UserRecord | None:
        statement = select(User).where(User.email == email)
        result = await self._session.exec(statement)
        user = result.first()
        if user is None:
            return None
        return _to_user_record(user)

    async def create(self, *, email: str, hashed_password: str) -> UserRecord:
        user = User(email=email, hashed_password=hashed_password)
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return _to_user_record(user)
