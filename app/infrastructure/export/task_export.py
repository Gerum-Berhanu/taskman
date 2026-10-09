import asyncio
import logging
from uuid import UUID

from app.infrastructure.database.session import async_session_factory
from app.infrastructure.email.smtp import send_tasks_export_email
from app.infrastructure.export.tasks_csv import tasks_to_csv
from app.observability.events import InfraLogEvent
from app.observability.log_event import log_event
from app.repositories.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


async def run_tasks_export(
    *,
    workspace_id: UUID,
    to_email: str,
    actor_id: str | None = None,
) -> None:
    """Background job: load workspace tasks, build CSV, email it (own DB session)."""
    try:
        async with async_session_factory() as session:
            async with UnitOfWork(session) as uow:
                rows = await uow.tasks.list_all(workspace_id)
        csv_text = tasks_to_csv(rows)

        subject = await asyncio.to_thread(
            send_tasks_export_email,
            to=to_email,
            workspace_id=str(workspace_id),
            csv_text=csv_text,
        )
    except Exception:
        log_event(
            logger,
            logging.ERROR,
            InfraLogEvent.TASK_EXPORT_FAILED,
            exc_info=True,
            workspace_id=workspace_id,
            email=to_email,
            actor_id=actor_id or "-",
        )
        return

    log_event(
        logger,
        logging.INFO,
        InfraLogEvent.TASK_EXPORT_SENT,
        workspace_id=workspace_id,
        email=to_email,
        actor_id=actor_id or "-",
        subject=subject,
    )