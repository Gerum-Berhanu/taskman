"""User registration application services."""

from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.dto.api.auth import RegisterVerify, UserCreateResponse
from app.exceptions import (
    EmailAlreadyRegisteredError,
    RegistrationOtpAttemptsExceededError,
    RegistrationOtpInvalidError,
    RegistrationStoreUnavailableError,
)
from app.core.security import (
    generate_registration_otp,
    get_password_hash,
    hash_registration_otp,
    verify_registration_otp,
)
from app.infrastructure.email.mails import send_registration_otp_email, send_welcome_email
from app.dto.api.user import UserCreate
from app.dto.repository import UserCreateData
from app.infrastructure.redis.errors import REDIS_DATA_ERRORS
from app.infrastructure.redis.registration.pending import (
    clear_pending,
    create_pending,
    get_pending,
    incr_attempt,
)
from app.observability.events import DomainLogEvent
from app.services.base import BaseService


class UserService(BaseService):
    """Register new users."""

    async def start_registration(self, payload: UserCreate, bg_tasks: BackgroundTasks) -> UUID:
        """Check email, create & mail OTP, return registration id / ticket"""
        email = payload.email
        password = payload.password

        if await self._uow.users.get_by_email(email) is not None:
            raise EmailAlreadyRegisteredError

        hashed_password = get_password_hash(password)

        plain_otp = generate_registration_otp()
        hashed_otp = hash_registration_otp(plain_otp)

        try:
            registration_id = await create_pending(
                email=email,
                hashed_password=hashed_password,
                otp_hash=hashed_otp,
            )
        except REDIS_DATA_ERRORS:
            raise RegistrationStoreUnavailableError

        bg_tasks.add_task(send_registration_otp_email, email, plain_otp)

        return registration_id

    async def complete_registration(
        self, payload: RegisterVerify, bg_tasks: BackgroundTasks
    ) -> UserCreateResponse:
        email, hashed_password, registration_id = await self._verify_registration(payload)
        return await self._register_user(
            email=email,
            hashed_password=hashed_password,
            registration_id=registration_id,
            bg_tasks=bg_tasks,
        )

    async def _verify_registration(
        self, payload: RegisterVerify
    ) -> tuple[str, str, UUID]:
        registration_id = payload.registration_id
        try:
            pending = await get_pending(registration_id)
            if not pending:
                raise RegistrationOtpInvalidError

            if pending["attempts"] >= settings.registration_otp_max_attempts:
                await clear_pending(registration_id)
                raise RegistrationOtpAttemptsExceededError

            if not verify_registration_otp(payload.otp, pending["otp_hash"]):
                await incr_attempt(registration_id)
                raise RegistrationOtpInvalidError

            return pending["email"], pending["hashed_password"], registration_id
        except REDIS_DATA_ERRORS:
            raise RegistrationStoreUnavailableError

    async def _clear_pending(self, registration_id: UUID) -> None:
        try:
            await clear_pending(registration_id)
        except REDIS_DATA_ERRORS:
            raise RegistrationStoreUnavailableError

    async def _register_user(
        self,
        *,
        email: str,
        hashed_password: str,
        registration_id: UUID,
        bg_tasks: BackgroundTasks,
    ) -> UserCreateResponse:
        """Create a user; conflict on concurrent races."""

        try:
            user = await self._uow.users.create(
                UserCreateData(email=email, hashed_password=hashed_password)
            )
        except IntegrityError:
            await self._clear_pending(registration_id)
            raise EmailAlreadyRegisteredError from None

        await self._clear_pending(registration_id)

        user_email = user.email
        self.log_after_commit(
            DomainLogEvent.USER_REGISTERED,
            user_id=user.id,
            email=user_email,
        )
        self._uow.after_commit(
            lambda: bg_tasks.add_task(send_welcome_email, user_email)
        )
        return UserCreateResponse(id=user.id, email=user.email)
