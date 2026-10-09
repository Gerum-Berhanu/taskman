"""User registration application services."""

import logging

from fastapi import BackgroundTasks
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import EmailAlreadyRegisteredError
from app.core.security import get_password_hash
from app.infrastructure.email.smtp import send_welcome_email
from app.dto.api.user import UserCreate, UserRead
from app.dto.repository import UserCreateData
from app.observability.events import DomainLogEvent
from app.repositories.unit_of_work import UnitOfWork


logger = logging.getLogger(__name__)


class UserService:
    """Register new users."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def register(self, payload: UserCreate, bg_tasks: BackgroundTasks) -> UserRead:
        """Create a user; conflict on duplicate email (including concurrent races)."""
        if await self._uow.users.get_by_email(payload.email) is not None:
            raise EmailAlreadyRegisteredError

        hashed_password = get_password_hash(payload.password)
        try:
            user = await self._uow.users.create(UserCreateData(
                email=payload.email, hashed_password=hashed_password
            ))
        except IntegrityError:
            raise EmailAlreadyRegisteredError from None

        user_id, email = user.id, user.email
        self._uow.after_commit(
            lambda: logger.info(
                "%s user_id=%s email=%s", DomainLogEvent.USER_REGISTERED, user_id, email
            )
        )

        self._uow.after_commit(
            lambda: bg_tasks.add_task(send_welcome_email, email)
        )
        return UserRead.model_validate(user, from_attributes=True)
