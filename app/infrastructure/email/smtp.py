from email.message import EmailMessage
from importlib.resources import files
import smtplib

from app.core.config import settings


def send_mail(*, to: str, subject: str, body: str):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = to
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)


def send_welcome_email(to: str) -> str:
    """Return the subject"""
    subject = "Welcome to Taskman"
    body = (
        files("app.infrastructure.email.templates")
        .joinpath("welcome.txt")
        .read_text(encoding="utf-8")
    )
    send_mail(to=to, subject=subject, body=body)
    return subject
