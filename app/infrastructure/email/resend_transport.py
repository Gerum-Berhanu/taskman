"""Resend HTTPS email transport (works where outbound SMTP is blocked)."""

from __future__ import annotations

import base64

import resend

from app.core.config import settings


def send_via_resend(
    *,
    to: str,
    subject: str,
    html: str,
    attachment_filename: str | None = None,
    attachment_bytes: bytes | None = None,
    attachment_mime: str = "text/csv",
) -> None:
    """Send one HTML message via the Resend SDK. Raises on transport/API failure."""
    resend.api_key = settings.resend_api_key

    params: resend.Emails.SendParams = {
        "from": settings.resend_from,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    if attachment_filename is not None and attachment_bytes is not None:
        attachment: resend.Attachment = {
            "filename": attachment_filename,
            "content": base64.b64encode(attachment_bytes).decode("ascii"),
        }
        if attachment_mime:
            attachment["content_type"] = attachment_mime
        params["attachments"] = [attachment]

    resend.Emails.send(params)
