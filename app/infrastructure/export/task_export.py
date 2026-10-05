import asyncio
import logging
from uuid import UUID

from app.infrastructure.database.session import async_session_factory
from app.infrastructure.email.smtp import send_tasks_export_email
from app.infrastructure.export.tasks_csv import tasks_to_csv
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
        logger.exception(
            "task_export_failed workspace_id=%s email=%s actor_id=%s",
            workspace_id,
            to_email,
            actor_id or "-",
        )
        return

    logger.info(
        "task_export_sent workspace_id=%s email=%s actor_id=%s subject=%s",
        workspace_id,
        to_email,
        actor_id or "-",
        repr(subject),
    )