"""Sync SMTP helpers (feature flag + transport logging live here)."""

from email.message import EmailMessage
from importlib.resources import files
import logging
import smtplib

from app.core.config import settings


logger = logging.getLogger(__name__)


def send_mail(*, to: str, subject: str, body: str) -> None:
    """Send one plain-text message. No-op when email is disabled; never raises."""
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
    msg.set_content(body)

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
    body = (
        files("app.infrastructure.email.templates")
        .joinpath("welcome.txt")
        .read_text(encoding="utf-8")
    )
    send_mail(to=to, subject=subject, body=body)
    return subject
