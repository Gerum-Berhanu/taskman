"""Welcome-email mailer and register hook tests (no real SMTP)."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.email.smtp import send_mail, send_welcome_email


def test_send_mail_uses_smtp_starttls_login_and_send(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.infrastructure.email.smtp.settings.email_enabled", True)
    monkeypatch.setattr("app.infrastructure.email.smtp.settings.smtp_host", "smtp.example.com")
    monkeypatch.setattr("app.infrastructure.email.smtp.settings.smtp_port", 587)
    monkeypatch.setattr("app.infrastructure.email.smtp.settings.smtp_user", "user@example.com")
    monkeypatch.setattr("app.infrastructure.email.smtp.settings.smtp_password", "secret")
    monkeypatch.setattr("app.infrastructure.email.smtp.settings.email_from", "from@example.com")

    smtp_instance = MagicMock()
    smtp_cm = MagicMock()
    smtp_cm.__enter__.return_value = smtp_instance
    smtp_cm.__exit__.return_value = None

    with patch("app.infrastructure.email.smtp.smtplib.SMTP", return_value=smtp_cm) as smtp_cls:
        send_mail(to="to@example.com", subject="Hello", body="Body text")

    smtp_cls.assert_called_once_with("smtp.example.com", 587, timeout=30)
    smtp_instance.starttls.assert_called_once_with()
    smtp_instance.login.assert_called_once_with("user@example.com", "secret")
    smtp_instance.send_message.assert_called_once()
    sent_msg = smtp_instance.send_message.call_args.args[0]
    assert sent_msg["Subject"] == "Hello"
    assert sent_msg["From"] == "from@example.com"
    assert sent_msg["To"] == "to@example.com"
    assert sent_msg.get_content().strip() == "Body text"


def test_send_mail_skips_when_email_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.infrastructure.email.smtp.settings.email_enabled", False)

    with patch("app.infrastructure.email.smtp.smtplib.SMTP") as smtp_cls:
        send_mail(to="to@example.com", subject="Hello", body="Body text")

    smtp_cls.assert_not_called()


def test_send_mail_swallows_smtp_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.infrastructure.email.smtp.settings.email_enabled", True)
    monkeypatch.setattr("app.infrastructure.email.smtp.settings.smtp_host", "smtp.example.com")
    monkeypatch.setattr("app.infrastructure.email.smtp.settings.smtp_port", 587)
    monkeypatch.setattr("app.infrastructure.email.smtp.settings.smtp_user", "user@example.com")
    monkeypatch.setattr("app.infrastructure.email.smtp.settings.smtp_password", "secret")
    monkeypatch.setattr("app.infrastructure.email.smtp.settings.email_from", "from@example.com")

    with patch(
        "app.infrastructure.email.smtp.smtplib.SMTP",
        side_effect=OSError("SMTP down"),
    ):
        send_mail(to="to@example.com", subject="Hello", body="Body text")


def test_send_welcome_email_loads_template_and_returns_subject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str] = {}

    def _fake_send_mail(*, to: str, subject: str, body: str) -> None:
        captured["to"] = to
        captured["subject"] = subject
        captured["body"] = body

    monkeypatch.setattr("app.infrastructure.email.smtp.send_mail", _fake_send_mail)

    subject = send_welcome_email("new@example.com")

    assert subject == "Welcome to Taskman"
    assert captured["to"] == "new@example.com"
    assert captured["subject"] == "Welcome to Taskman"
    assert "We are happy to welcome you to Taskman!" in captured["body"]
    assert "Your account is ready." in captured["body"]


def test_register_schedules_welcome_email(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def _fake_send_welcome(to: str) -> str:
        calls.append(to)
        return "Welcome to Taskman"

    monkeypatch.setattr("app.services.user.send_welcome_email", _fake_send_welcome)

    response = client.post(
        "/auth/register",
        json={"email": "welcome@example.com", "password": "password123"},
    )

    assert response.status_code == 201, response.text
    assert calls == ["welcome@example.com"]


def test_register_succeeds_when_smtp_fails(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.infrastructure.email.smtp.settings.email_enabled", True)
    monkeypatch.setattr("app.infrastructure.email.smtp.settings.smtp_host", "smtp.example.com")
    monkeypatch.setattr("app.infrastructure.email.smtp.settings.smtp_port", 587)
    monkeypatch.setattr("app.infrastructure.email.smtp.settings.smtp_user", "user@example.com")
    monkeypatch.setattr("app.infrastructure.email.smtp.settings.smtp_password", "secret")
    monkeypatch.setattr("app.infrastructure.email.smtp.settings.email_from", "from@example.com")

    with patch(
        "app.infrastructure.email.smtp.smtplib.SMTP",
        side_effect=OSError("SMTP down"),
    ):
        response = client.post(
            "/auth/register",
            json={"email": "still-created@example.com", "password": "password123"},
        )

    assert response.status_code == 201, response.text
    assert response.json()["email"] == "still-created@example.com"
