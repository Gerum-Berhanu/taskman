import asyncio
from uuid import UUID
from app.infrastructure.email.mails import send_registration_otp_email, send_welcome_email
from app.jobs.export.task_export import run_tasks_export
from app.workers.celery_app import celery_app


@celery_app.task(name="taskman.export_workspace_tasks")
def export_workspace_tasks(
    workspace_id: str, to_email: str, actor_id: str | None = None
) -> None:
    asyncio.run(
        run_tasks_export(
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
