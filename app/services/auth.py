from datetime import timedelta
from typing import Any
from uuid import UUID

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
from app.repositories import ClientSessionRecord, RefreshTokenRecord
from app.repositories.refresh_token import RefreshTokenCreateData
from app.repositories.user import UserRecord
from app.schemas.auth import Token
from app.schemas.user import UserRead


_DUMMY_HASH = get_password_hash("__timing_guard__")


class AuthService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def authenticate(self, email: EmailStr, password: str) -> UserRecord:
        """Verify email/password and return the user record (with credentials)."""
        user = await self._uow.users.get_by_email(email)
        if not user:
            verify_password(password, _DUMMY_HASH)
            raise InvalidCredentialsError
        if not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError
        # Same error as bad credentials - don't leak that the account is disabled.
        if not user.is_active:
            raise InvalidCredentialsError
        return user

    async def login(self, email: EmailStr, password: str) -> Token:
        """Authenticate and issue a new access + refresh token pair."""
        user = await self.authenticate(email, password)
        raw_token = generate_refresh_token()
        token_hash = hash_refresh_token(raw_token)

        client_session = await self._uow.client_sessions.create(user_id=user.id)

        refresh_token = await self._uow.refresh_tokens.create(RefreshTokenCreateData(
            client_session_id=client_session.id, token_hash=token_hash
        ))

        await self._uow.client_sessions.set_active_token_id(
            client_id=client_session.id,
            token_id=refresh_token.id
        )

        access_token = self.create_access_token(data={"sub": str(user.id)})

        return Token(
            access_token=access_token,
            refresh_token=raw_token,
        )
    
    async def _get_token_and_session_rows(
        self, token: str
    ) -> tuple[RefreshTokenRecord, ClientSessionRecord]:
        """Resolve a raw refresh token to its token row and client session."""
        row = await self._uow.refresh_tokens.get_by_token_hash(hash_refresh_token(token))
        if row is None:
            raise InvalidTokenError
        
        session = await self._uow.client_sessions.get_by_id(row.client_session_id)
        if session is None:
            raise InvalidTokenError

        return row, session

    async def _revoke_and_reject(self, session_id: UUID) -> None:
        """Persist revocation, then fail the request (UoW would otherwise roll back)."""
        await self._uow.client_sessions.revoke(session_id)
        await self._uow.session.commit()
        raise InvalidTokenError

    async def _require_active_refresh(self, token: str) -> ClientSessionRecord:
        """Validate a refresh token; revoke the session on reuse, expiry, or inactive user."""
        row, session = await self._get_token_and_session_rows(token)

        if session.revoked_at is not None:
            raise InvalidTokenError

        # Presented token belongs to a live session but is not the active one → reuse/theft.
        if row.id != session.active_token_id:
            await self._revoke_and_reject(session.id)

        if ensure_utc(session.expires_at) <= utcnow():
            await self._revoke_and_reject(session.id)

        user = await self._uow.users.get_by_id(session.user_id)
        if user is None or not user.is_active:
            await self._revoke_and_reject(session.id)

        return session

    async def refresh(self, token: str) -> Token:
        """Rotate refresh token and issue a new access token."""
        client_session = await self._require_active_refresh(token)
        
        new_raw_token = generate_refresh_token()
        new_token_row = await self._uow.refresh_tokens.create(RefreshTokenCreateData(
            client_session_id=client_session.id,
            token_hash=hash_refresh_token(new_raw_token),
        ))

        updated_session = await self._uow.client_sessions.set_active_token_id(
            client_id=client_session.id,
            token_id=new_token_row.id,
            is_rotation=True,
        )
        if updated_session is None:
            raise InvalidTokenError

        new_access_token = self.create_access_token({"sub": str(client_session.user_id)})
        
        return Token(
            access_token=new_access_token,
            refresh_token=new_raw_token,
        )

    async def logout(self, token: str) -> None:
        """Revoke the client session for this refresh token; reuse revokes then rejects."""
        token_row, session = await self._get_token_and_session_rows(token)

        if session.revoked_at is not None:
            raise InvalidTokenError

        # Non-active refresh on a live session → same reuse/theft response as refresh.
        if token_row.id != session.active_token_id:
            await self._revoke_and_reject(session.id)

        revoked = await self._uow.client_sessions.revoke(client_id=session.id)
        if not revoked:
            raise InvalidTokenError
            
    async def logout_all_user_sessions(self, token: str) -> None:
        """Revoke every client session for the user; reuse revokes then rejects."""
        token_row, session = await self._get_token_and_session_rows(token)

        if session.revoked_at is not None:
            raise InvalidTokenError

        # Non-active refresh on a live session → same reuse/theft response as refresh/logout.
        if token_row.id != session.active_token_id:
            await self._revoke_and_reject(session.id)

        if ensure_utc(session.expires_at) <= utcnow():
            await self._revoke_and_reject(session.id)

        await self._uow.client_sessions.revoke_all_user_sessions(session.user_id)
        
    def create_access_token(
        self, data: dict[str, Any], expires_delta: timedelta | None = None
    ) -> str:
        """Encode a JWT access token with the configured expiry."""
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

    def _get_id_from_token(self, token: str) -> UUID:
        """Decode an access token and return the user id from `sub`."""
        try:
            payload = jwt.decode(
                token, settings.secret_key, algorithms=[settings.algorithm]
            )
        except jwt.PyJWTError:
            raise InvalidTokenError from None

        sub = payload.get("sub")
        if not isinstance(sub, str):
            raise InvalidTokenError
        try:
            return UUID(sub)
        except ValueError:
            raise InvalidTokenError from None

    async def get_user_from_token(self, token: str) -> UserRead:
        """Load the active user for an access token as a credential-free UserRead."""
        user_id = self._get_id_from_token(token)
        user = await self._uow.users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise InvalidTokenError
        return UserRead.model_validate(user, from_attributes=True)
