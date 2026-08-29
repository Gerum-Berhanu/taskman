from app.core.exceptions import EmailAlreadyRegisteredError
from app.core.security import get_password_hash
from app.repositories.records import UserRecord
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserCreate


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    async def register(self, data: UserCreate) -> UserRecord:
        if await self._repository.get_by_email(data.email) is not None:
            raise EmailAlreadyRegisteredError

        hashed_password = get_password_hash(data.password)
        return await self._repository.create(email=data.email, hashed_password=hashed_password)
