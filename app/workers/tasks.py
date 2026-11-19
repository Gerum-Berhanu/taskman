import asyncio
from collections.abc import Callable, Coroutine
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import UUID

from app.infrastructure.email.mails import send_registration_otp_email, send_welcome_email
from app.jobs.export.task_export import run_tasks_export
from app.workers.celery_app import celery_app


def _run_async(factory: Callable[[], Coroutine[Any, Any, None]]) -> None:
    """Run an async job from sync Celery code.

    Normal workers have no running loop, so ``asyncio.run`` is enough.
    Eager mode under TestClient already owns a loop; nest ``asyncio.run``
    there raises, so run the coroutine on a one-shot thread instead.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(factory())
        return

    with ThreadPoolExecutor(max_workers=1) as executor:
        executor.submit(lambda: asyncio.run(factory())).result()


@celery_app.task(name="taskman.export_workspace_tasks")
def export_workspace_tasks(
    workspace_id: str, to_email: str, actor_id: str | None = None
) -> None:
    _run_async(
        lambda: run_tasks_export(
            workspace_id=UUID(workspace_id),
            to_email=to_email,
            actor_id=actor_id,
        )
    )


@celery_app.task(name="taskman.send_registration_otp_email_task")
def send_registration_otp_email_task(email: str, otp: str) -> None:
    send_registration_otp_email(email, otp)


@celery_app.task(name="taskman.send_welcome_email_task")
def send_welcome_email_task(email: str) -> None:
    send_welcome_email(email)
