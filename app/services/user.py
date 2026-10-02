"""User registration application services."""

import logging

from fastapi import BackgroundTasks
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import EmailAlreadyRegisteredError
from app.core.security import get_password_hash
from app.infrastructure.email.smtp import send_welcome_email
from app.repositories.unit_of_work import UnitOfWork
from app.repositories.user import UserCreateData, UserRecord
from app.schemas.user import UserCreate


logger = logging.getLogger(__name__)


class UserService:
    """Register new users."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def register(self, data: UserCreate, bg_tasks: BackgroundTasks) -> UserRecord:
        """Create a user; conflict on duplicate email (including concurrent races)."""
        if await self._uow.users.get_by_email(data.email) is not None:
            raise EmailAlreadyRegisteredError

        hashed_password = get_password_hash(data.password)
        try:
            user = await self._uow.users.create(UserCreateData(
                email=data.email, hashed_password=hashed_password
            ))
        except IntegrityError:
            raise EmailAlreadyRegisteredError from None

        user_id, email = user.id, user.email
        self._uow.after_commit(
            lambda: logger.info(
                "user_registered user_id=%s email=%s", user_id, email
            )
        )

        self._uow.after_commit(
            lambda: bg_tasks.add_task(self._bg_welcome_email, email)
        )
        return user

    def _bg_welcome_email(self, email: str):
        try:
            subject = send_welcome_email(email)
        except Exception:
            logger.exception("email_send_failed email=%s", email)
            return
        logger.info("email_sent email=%s subject=%s", email, repr(subject))
