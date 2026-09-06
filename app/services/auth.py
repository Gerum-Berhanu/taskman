from datetime import timedelta
from typing import Any

import jwt
from pydantic import EmailStr

from app.core.config import settings
from app.core.exceptions import InvalidCredentialsError, InvalidTokenError
from app.core.security import generate_refresh_token, get_password_hash, verify_password
from app.core.timeutils import utcnow
from app.database.unit_of_work import UnitOfWork
from app.repositories.records import UserRecord
from app.schemas.auth import Token


_DUMMY_HASH = get_password_hash("__timing_guard__")


class AuthService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def authenticate(self, email: EmailStr, password: str) -> UserRecord:
        user = await self._uow.users.get_by_email(email)
        if not user:
            verify_password(password, _DUMMY_HASH)
            raise InvalidCredentialsError
        if not verify_password(password, user["hashed_password"]):
            raise InvalidCredentialsError
        return user

    async def login(self, email: EmailStr, password: str) -> Token:
        user = await self.authenticate(email, password)
        refresh_token = generate_refresh_token()
        await self._uow.user_sessions.create(
            user_id=user["id"],
            token=refresh_token,
        )
        access_token = self.create_access_token(data={"sub": user["email"]})
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )

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

    def _get_email_from_token(self, token: str) -> str:
        try:
            payload = jwt.decode(
                token, settings.secret_key, algorithms=[settings.algorithm]
            )
            email = payload.get("sub")
            if not isinstance(email, str):
                raise InvalidTokenError
            return email
        except jwt.InvalidTokenError:
            raise InvalidTokenError

    async def get_user_from_token(self, token: str) -> UserRecord:
        email = self._get_email_from_token(token)
        user = await self._uow.users.get_by_email(email)
        if user is None:
            raise InvalidTokenError
        return user
