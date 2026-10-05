"""Sync SMTP helpers (feature flag + transport logging live here)."""

from email.message import EmailMessage
import logging
import smtplib

from jinja2 import Environment, PackageLoader, select_autoescape

from app.core.config import settings


logger = logging.getLogger(__name__)


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
    """Send one HTML message. No-op when email is disabled; never raises."""
    if not settings.email_enabled:
        logger.info(
            "email_skipped email=%s reason=email_disabled subject=%s",
            to,
            repr(subject),
        )
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.email_from or settings.smtp_user
    msg["To"] = to
    msg.set_content(html, subtype="html")

    if attachment_filename is not None and attachment_bytes is not None:
        maintype, _, subtype = attachment_mime.partition("/")
        msg.add_attachment(
            attachment_bytes,
            maintype=maintype or "text",
            subtype=subtype or "csv",
            filename=attachment_filename,
        )

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
    except Exception:
        logger.exception(
            "email_send_failed email=%s subject=%s",
            to,
            repr(subject),
        )
        return

    logger.info("email_sent email=%s subject=%s", to, repr(subject))


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
