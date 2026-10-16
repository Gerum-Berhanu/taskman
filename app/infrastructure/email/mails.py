"""Email compose helpers (feature flag + transport logging live here)."""

import logging
import smtplib

from jinja2 import Environment, PackageLoader, select_autoescape
from resend.exceptions import ResendError

from app.core.config import settings
from app.infrastructure.email.providers.resend import send_via_resend
from app.infrastructure.email.providers.smtp import send_via_smtp
from app.observability.events import InfraLogEvent
from app.observability.log_event import log_event


logger = logging.getLogger(__name__)

# Transport failures only; programming errors in callers still propagate.
_SEND_ERRORS = (smtplib.SMTPException, OSError, TimeoutError, ResendError)


_env = Environment(
    loader=PackageLoader("app.infrastructure.email", "templates"),
    autoescape=select_autoescape(["html", "xml"]),
)


def send_mail(
    *,
    to: str,
    subject: str,
    html: str,
    attachment_filename: str | None = None,
    attachment_bytes: bytes | None = None,
    attachment_mime: str = "text/csv",
) -> None:
    """Send one HTML message. No-op when email is disabled; never raises.

    Prefers Resend HTTPS when ``RESEND_API_KEY`` is set; otherwise SMTP.
    """
    if not settings.email_enabled:
        log_event(
            logger,
            logging.INFO,
            InfraLogEvent.EMAIL_SKIPPED,
            email=to,
            reason="email_disabled",
            subject=subject,
        )
        return

    try:
        if settings.resend_api_key:
            send_via_resend(
                to=to,
                subject=subject,
                html=html,
                attachment_filename=attachment_filename,
                attachment_bytes=attachment_bytes,
                attachment_mime=attachment_mime,
            )
        else:
            send_via_smtp(
                to=to,
                subject=subject,
                html=html,
                attachment_filename=attachment_filename,
                attachment_bytes=attachment_bytes,
                attachment_mime=attachment_mime,
            )
    except _SEND_ERRORS:
        log_event(
            logger,
            logging.ERROR,
            InfraLogEvent.EMAIL_SEND_FAILED,
            exc_info=True,
            email=to,
            subject=subject,
        )
        return

    log_event(
        logger,
        logging.INFO,
        InfraLogEvent.EMAIL_SENT,
        email=to,
        subject=subject,
    )


def send_welcome_email(to: str) -> str:
    """Build the welcome message and send it. Returns the subject."""
    subject = "Welcome to Taskman"
    html = _env.get_template("welcome.html").render()
    send_mail(to=to, subject=subject, html=html)
    return subject


def send_tasks_export_email(*, to: str, workspace_id: str, csv_text: str) -> str:
    """Build the export message with CSV attachment and send it. Returns the subject."""
    subject = f"Taskman export [{workspace_id}]"
    html = _env.get_template("tasks_export.html").render(workspace_id=workspace_id)
    send_mail(
        to=to,
        subject=subject,
        html=html,
        attachment_filename=f"tasks-{workspace_id}.csv",
        attachment_bytes=csv_text.encode("utf-8"),
        attachment_mime="text/csv",
    )
    return subject
