"""Authentication, token issuance, and session lifecycle."""

from datetime import timedelta
import logging
from typing import Any
from uuid import UUID

import jwt
from pydantic import EmailStr

from app.core.config import settings
from app.dto.api.auth import ClientSessionRead
from app.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    SessionNotFoundError,
)
from app.core.security import (
    generate_refresh_token,
    get_password_hash,
    hash_refresh_token,
    verify_password,
)
from app.core.timeutils import ensure_utc, utcnow
from app.repositories.unit_of_work import UnitOfWork
from app.dto.repository import (
    ClientSessionCreateData,
    ClientSessionRecord,
    RefreshTokenCreateData,
    RefreshTokenRecord,
    UserRecord,
)
from app.dto.api.user import UserRead
from app.observability.events import DomainLogEvent
from app.observability.log_event import log_event


logger = logging.getLogger(__name__)

_DUMMY_HASH = get_password_hash("__timing_guard__")


class AuthService:
    """Login, refresh, logout, and access-token validation."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def _authenticate(self, email: EmailStr, password: str) -> UserRecord:
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
    
    async def login(
        self,
        email: EmailStr,
        password: str,
        device_id: UUID | None = None,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[str, str, UUID]:
        """Authenticate and issue access + raw refresh (route sets the refresh cookie)."""
        user = await self._authenticate(email, password)
        user_id = user.id
        raw_token = generate_refresh_token()
        token_hash = hash_refresh_token(raw_token)

        session_data = ClientSessionCreateData(
            user_id=user_id,
            user_agent=self._clip(user_agent, 512),
            ip_address=self._clip(ip_address, 45),
        )
        if device_id is not None:
            await self._uow.client_sessions.delete_by_device(device_id)
            session_data.device_id = device_id
        client_session = await self._uow.client_sessions.create(session_data)
        
        refresh_token = await self._uow.refresh_tokens.create(RefreshTokenCreateData(
            client_session_id=client_session.id, token_hash=token_hash
        ))

        await self._uow.client_sessions.set_active_token_id(
            client_id=client_session.id,
            token_id=refresh_token.id
        )

        access_token = self._create_access_token(data={"sub": str(user_id)})

        self._uow.after_commit(
            lambda: log_event(
                logger,
                logging.INFO,
                DomainLogEvent.USER_LOGIN_SUCCEEDED,
                user_id=user_id,
            )
        )
        return access_token, raw_token, client_session.device_id

    def _clip(self, value: str | None, max_len: int) -> str | None:
        if value is None or not value.strip():
            return None
        return value[:max_len]

    async def list_sessions(
        self, user_id: UUID, current_device_id: UUID | None
    ) -> list[ClientSessionRead]:
        sessions = await self._uow.client_sessions.list_by_user(user_id)
        return [
            ClientSessionRead.model_validate(
                {
                    **session.model_dump(),
                    "is_current": current_device_id == session.device_id,
                }
            )
            for session in sessions
        ]

    async def delete_session(
        self,
        user_id: UUID,
        session_id: UUID,
        *,
        current_device_id: UUID | None = None,
    ) -> bool:
        """Delete one of the user's sessions. True if it was the current device."""
        session = await self._uow.client_sessions.get(session_id)
        if session is None or session.user_id != user_id:
            raise SessionNotFoundError

        was_current = (
            current_device_id is not None and session.device_id == current_device_id
        )
        deleted = await self._uow.client_sessions.delete(session_id)
        if not deleted:
            raise SessionNotFoundError

        self._uow.after_commit(
            lambda: log_event(
                logger,
                logging.INFO,
                DomainLogEvent.USER_LOGOUT,
                user_id=user_id,
                session_id=session_id,
            )
        )
        return was_current

    async def _get_token_and_session_rows(
        self, token: str
    ) -> tuple[RefreshTokenRecord, ClientSessionRecord]:
        """Resolve a raw refresh token to its token row and client session."""
        row = await self._uow.refresh_tokens.get_by_token_hash(hash_refresh_token(token))
        if row is None:
            raise InvalidTokenError
        
        session = await self._uow.client_sessions.get(row.client_session_id)
        if session is None:
            raise InvalidTokenError

        return row, session

    async def _delete_and_reject(self, session_id: UUID) -> None:
        """Delete the session, commit, then fail (UoW would otherwise roll back)."""
        await self._uow.client_sessions.delete(session_id)
        await self._uow.commit()
        raise InvalidTokenError

    async def _require_active_refresh(self, token: str) -> ClientSessionRecord:
        """Validate a refresh token; delete the session on reuse, expiry, or inactive user."""
        row, session = await self._get_token_and_session_rows(token)

        # Presented token belongs to a live session but is not the active one → reuse/theft.
        if row.id != session.active_token_id:
            await self._delete_and_reject(session.id)

        if ensure_utc(session.expires_at) <= utcnow():
            await self._delete_and_reject(session.id)

        user = await self._uow.users.get(session.user_id)
        if user is None or not user.is_active:
            await self._delete_and_reject(session.id)

        return session

    async def refresh(self, token: str) -> tuple[str, str]:
        """Rotate refresh and issue a new access token (route sets the refresh cookie)."""
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

        new_access_token = self._create_access_token({"sub": str(client_session.user_id)})

        return new_access_token, new_raw_token

    async def logout(self, token: str) -> None:
        """Delete the client session for this refresh token; reuse deletes then rejects."""
        token_row, session = await self._get_token_and_session_rows(token)

        # Non-active refresh on a live session → same reuse/theft response as refresh.
        if token_row.id != session.active_token_id:
            await self._delete_and_reject(session.id)

        deleted = await self._uow.client_sessions.delete(session.id)
        if not deleted:
            raise InvalidTokenError

        user_id, session_id = session.user_id, session.id
        self._uow.after_commit(
            lambda: log_event(
                logger,
                logging.INFO,
                DomainLogEvent.USER_LOGOUT,
                user_id=user_id,
                session_id=session_id,
            )
        )

    async def logout_all_user_sessions(self, token: str) -> None:
        """Delete every client session for the user; reuse deletes then rejects."""
        token_row, session = await self._get_token_and_session_rows(token)

        # Non-active refresh on a live session → same reuse/theft response as refresh/logout.
        if token_row.id != session.active_token_id:
            await self._delete_and_reject(session.id)

        if ensure_utc(session.expires_at) <= utcnow():
            await self._delete_and_reject(session.id)

        await self._uow.client_sessions.delete_all_user_sessions(session.user_id)
        user_id, session_id = session.user_id, session.id
        self._uow.after_commit(
            lambda: log_event(
                logger,
                logging.INFO,
                DomainLogEvent.USER_LOGOUT_ALL,
                user_id=user_id,
                session_id=session_id,
            )
        )

    def _create_access_token(
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
        user = await self._uow.users.get(user_id)
        if user is None or not user.is_active:
            raise InvalidTokenError
        return UserRead.model_validate(user, from_attributes=True)
