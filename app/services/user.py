import logging

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import EmailAlreadyRegisteredError
from app.core.security import get_password_hash
from app.database.unit_of_work import UnitOfWork
from app.repositories.user import UserCreateData, UserRecord
from app.schemas.user import UserCreate


logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def register(self, data: UserCreate) -> UserRecord:
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

        logger.info("user_registered user_id=%s email=%s", user.id, user.email)
        return user
