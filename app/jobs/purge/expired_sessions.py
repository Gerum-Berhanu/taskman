import asyncio
import logging
import sys

from app.infrastructure.database.session import async_session_factory
from app.observability.events import OpsLogEvent
from app.observability.log_event import log_event
from app.observability.setup import setup_logging
from app.repositories import UnitOfWork


logger = logging.getLogger(__name__)


async def run_purge_expired_sessions() -> None:
    try:
        async with async_session_factory() as session:
            async with UnitOfWork(session) as uow:
                count = await uow.client_sessions.delete_expired()
    except Exception:
        log_event(
            logger,
            logging.ERROR,
            OpsLogEvent.CLIENT_SESSIONS_PURGE_FAILED,
            exc_info=True,
        )
        raise

    log_event(
        logger,
        logging.INFO,
        OpsLogEvent.CLIENT_SESSIONS_PURGED,
        deleted=count,
    )


if __name__ == "__main__":
    try:
        setup_logging()
        asyncio.run(run_purge_expired_sessions())
    except Exception:
        sys.exit(1)
    