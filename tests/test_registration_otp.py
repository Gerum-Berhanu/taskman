"""Email OTP registration ticket flow (API-level)."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from redis.exceptions import RedisError

from app.core.config import settings
from tests.test_api import FIXED_OTP, PASSWORD, login, register, start_register


def test_start_registration_returns_202_ticket(client: TestClient) -> None:
    body = start_register(client, email="otp-start@example.com")

    assert body["message"] == "Check your email for a verification code"
    assert body["registration_id"]


def test_verify_registration_creates_user_and_allows_login(client: TestClient) -> None:
    user = register(client, email="otp-ok@example.com")

    assert user["email"] == "otp-ok@example.com"
    assert user["message"] == "User registered successfully"
    assert login(client, email="otp-ok@example.com")


def test_verify_rejects_bad_otp(client: TestClient) -> None:
    pending = start_register(client, email="otp-bad@example.com")

    with patch(
        "app.services.user.send_welcome_email",
        return_value="Welcome to Taskman",
    ):
        response = client.post(
            "/auth/register/verify",
            json={
                "registration_id": pending["registration_id"],
                "otp": "000000",
            },
        )

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Invalid or expired registration code"


def test_verify_rejects_unknown_ticket(client: TestClient) -> None:
    with patch(
        "app.services.user.send_welcome_email",
        return_value="Welcome to Taskman",
    ):
        response = client.post(
            "/auth/register/verify",
            json={"registration_id": str(uuid4()), "otp": FIXED_OTP},
        )

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Invalid or expired registration code"


def test_start_rejects_duplicate_email_after_verify(client: TestClient) -> None:
    register(client, email="otp-dup@example.com")

    with (
        patch("app.services.user.generate_registration_otp", return_value=FIXED_OTP),
        patch(
            "app.services.user.send_registration_otp_email",
            return_value="Your Taskman verification code",
        ),
    ):
        duplicate = client.post(
            "/auth/register",
            json={"email": "otp-dup@example.com", "password": PASSWORD},
        )

    assert duplicate.status_code == 409, duplicate.text
    assert duplicate.json()["detail"] == "Account with this email already exists"


def test_attempts_exceeded_clears_ticket(client: TestClient) -> None:
    pending = start_register(client, email="otp-cap@example.com")
    registration_id = pending["registration_id"]
    max_attempts = settings.registration_otp_max_attempts

    for _ in range(max_attempts):
        with patch(
            "app.services.user.send_welcome_email",
            return_value="Welcome to Taskman",
        ):
            bad = client.post(
                "/auth/register/verify",
                json={"registration_id": registration_id, "otp": "000000"},
            )
        assert bad.status_code == 400
        assert bad.json()["detail"] == "Invalid or expired registration code"

    with patch(
        "app.services.user.send_welcome_email",
        return_value="Welcome to Taskman",
    ):
        exceeded = client.post(
            "/auth/register/verify",
            json={"registration_id": registration_id, "otp": "000000"},
        )

    assert exceeded.status_code == 400, exceeded.text
    assert exceeded.json()["detail"] == "Registration attempts exceeded"


def test_verify_redis_failure_is_503(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    pending = start_register(client, email="otp-redis@example.com")

    async def _boom(*_args, **_kwargs):
        raise RedisError("redis down")

    monkeypatch.setattr(
        "app.services.user.get_pending",
        _boom,
    )

    response = client.post(
        "/auth/register/verify",
        json={
            "registration_id": pending["registration_id"],
            "otp": FIXED_OTP,
        },
    )

    assert response.status_code == 503, response.text
    assert response.json()["detail"] == "Registration temporarily unavailable"
