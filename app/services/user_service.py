from app.core.exceptions import EmailAlreadyRegisteredError
from app.core.security import get_password_hash
from app.database.records import UserRecord
from app.database.repositories.protocols import UserRepository
from app.models.user import UserCreate


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def register(self, data: UserCreate) -> UserRecord:
        if self._repository.get_by_email(data.email) is not None:
            raise EmailAlreadyRegisteredError(data.email)

        hashed_password = get_password_hash(data.password)
        return self._repository.create(email=data.email, hashed_password=hashed_password)
