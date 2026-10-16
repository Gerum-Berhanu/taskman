"""SMTP email transport."""

from email.message import EmailMessage
import smtplib

from app.core.config import settings


def send_via_smtp(
    *,
    to: str,
    subject: str,
    html: str,
    attachment_filename: str | None = None,
    attachment_bytes: bytes | None = None,
    attachment_mime: str = "text/csv",
) -> None:
    """Send one HTML message over SMTP. Raises on transport failure."""
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

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)
