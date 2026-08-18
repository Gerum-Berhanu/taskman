from datetime import timedelta
from typing import Any

import jwt
from pydantic import EmailStr

from app.core.config import settings
from app.core.security import get_dummy_hash, verify_password
from app.core.timeutils import utcnow
from app.database.records import UserRecord
from app.database.repositories import UserRepository


DUMMY_HASH = get_dummy_hash("my_dummy_password")


class AuthService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def authenticate(self, email: EmailStr, password: str) -> UserRecord | None:
        user = self._repository.get_by_email(email)
        if not user:
            verify_password(password, DUMMY_HASH)
            return None
        if not verify_password(password, user["hashed_password"]):
            return None
        return user

    def create_access_token(
        self, data: dict[str, Any], expires_delta: timedelta | None = None
    ) -> str:
        to_encode = data.copy()

        expire = utcnow()
        expire += (
            expires_delta
            if expires_delta is not None
            else timedelta(minutes=settings.access_token_expire_minutes)
        )

        to_encode.update({"exp": expire})
        return jwt.encode(
            payload=to_encode,
            key=settings.secret_key,
            algorithm=settings.algorithm,
        )

    def get_email_from_token(self, token: str) -> str | None:
        try:
            payload = jwt.decode(
                token, settings.secret_key, algorithms=[settings.algorithm]
            )
            email = payload.get("sub")
            if not isinstance(email, str):
                return None
            return email
        except jwt.InvalidTokenError:
            return None

    def get_user_from_token(self, token: str) -> UserRecord | None:
        email = self.get_email_from_token(token)
        if email is None:
            return None
        return self._repository.get_by_email(email)
