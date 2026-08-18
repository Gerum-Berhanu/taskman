from typing import Any

from app.core.exceptions import EmailAlreadyRegisteredError
from app.core.security import get_password_hash
from app.database.stores import UserStore
from app.models.user import UserCreate


class UserService:
    def __init__(self, store: UserStore) -> None:
        self._store = store

    def get_by_email(self, email: str) -> dict[str, Any] | None:
        return self._store.get_by_email(email)

    def register(self, data: UserCreate) -> dict[str, Any]:
        if self._store.get_by_email(data.email) is not None:
            raise EmailAlreadyRegisteredError(data.email)

        hashed_password = get_password_hash(data.password)
        return self._store.create(email=data.email, hashed_password=hashed_password)
