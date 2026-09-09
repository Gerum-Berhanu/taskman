from datetime import timedelta
from typing import Any
import logging
from uuid import UUID, uuid4

import jwt
from pydantic import EmailStr

from app.core.config import settings
from app.core.exceptions import InvalidCredentialsError, InvalidTokenError
from app.core.security import (
    generate_refresh_token,
    get_password_hash,
    hash_refresh_token,
    verify_password,
)
from app.core.timeutils import ensure_utc, utcnow
from app.database.unit_of_work import UnitOfWork
from app.repositories.user import UserRecord
from app.repositories.user_session import UserSessionRecord
from app.schemas.auth import Token


logger = logging.getLogger(__name__)
_DUMMY_HASH = get_password_hash("__timing_guard__")


class AuthService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def authenticate(self, email: EmailStr, password: str) -> UserRecord:
        user = await self._uow.users.get_by_email(email)
        if not user:
            verify_password(password, _DUMMY_HASH)
            raise InvalidCredentialsError
        if not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError
        # Same error as bad credentials — don't leak that the account is disabled.
        if not user.is_active:
            raise InvalidCredentialsError
        return user

    async def login(self, email: EmailStr, password: str) -> Token:
        user = await self.authenticate(email, password)
        raw_token = generate_refresh_token()
        token_hash = hash_refresh_token(raw_token)

        client_session = await self._uow.client_sessions.create(user_id=user.id)
        refresh_token = await self._uow.refresh_tokens.create(
            client_session_id=client_session.id, token_hash=token_hash
        )

        await self._uow.client_sessions.set_active_token_id(
            client_id=client_session.id,
            token_id=refresh_token.id
        )

        access_token = self.create_access_token(data={"sub": user.email})

        return Token(
            access_token=access_token,
            refresh_token=raw_token,
        )

    async def refresh(self, token: str) -> Token:
        try:
            family_id = extract_family_id(token)
        except ValueError:
            raise InvalidTokenError from None

        family = await self._uow.user_sessions.get(family_id)
        if (
            family is None
            or family["is_revoked"]
            or ensure_utc(family["expires_at"]) <= utcnow()
        ):
            raise InvalidTokenError

        presented_hash = hash_refresh_token(token)

        if presented_hash == family["active_token_hash"]:
            user = await self._uow.users.get_by_id(family["user_id"])
            if user is None:
                # Invariant: session.user_id must exist; data integrity problem if not.
                logger.error(
                    "Refresh session %s references missing user %s",
                    family["id"],
                    family["user_id"],
                )
                raise InvalidTokenError
            if not user.is_active:
                raise InvalidTokenError

            new_refresh_token = build_refresh_token(family_id)
            updated = await self._uow.user_sessions.rotate(
                family_id, new_token=new_refresh_token
            )
            if updated is None:
                raise InvalidTokenError

            return Token(
                access_token=self.create_access_token({"sub": user.email}),
                refresh_token=new_refresh_token,
            )

        await self._revoke_on_reuse(family, presented_hash)
        raise InvalidTokenError

    async def logout(self, token: str) -> None:
        try:
            family_id = extract_family_id(token)
        except ValueError:
            raise InvalidTokenError from None

        family = await self._uow.user_sessions.get(family_id)
        if family is None:
            raise InvalidTokenError

        if family["is_revoked"]:
            return  # idempotent

        presented_hash = hash_refresh_token(token)
        if presented_hash == family["active_token_hash"]:
            await self._uow.user_sessions.revoke(family_id)
            return

        await self._revoke_on_reuse(family, presented_hash)
        raise InvalidTokenError

    async def logout_all(self, user_id: UUID) -> None:
        await self._uow.user_sessions.revoke_all_by_user(user_id)

    async def _revoke_on_reuse(
        self, family: UserSessionRecord, presented_hash: str
    ) -> None:
        """If this hash was already rotated away, revoke the family.

        Commits before raising so the revoke survives UnitOfWork rollback on error.
        """
        if any(entry["hash"] == presented_hash for entry in family["used_token_hashes"]):
            await self._uow.user_sessions.revoke(family["id"])
            await self._uow.session.commit()
            logger.warning("Refresh token reuse detected for session %s", family["id"])
            raise InvalidTokenError

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
        if user is None or not user.is_active:
            raise InvalidTokenError
        return user
