"""Rate-limit tests opt in via monkeypatch; suite keeps RATE_LIMIT_ENABLED=false."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from redis import Redis

from app.core.config import settings


def _flush_testclient_rate_keys() -> None:
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        # Keys match rate_limit_algorithms._hit: rl_{script_name}:{policy}:{identity}
        client.delete(
            "rl_sliding_window_counter:default:testclient",
            "rl_sliding_window_counter:auth:testclient",
        )
    finally:
        client.close()


@pytest.fixture
def enable_rate_limits(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Turn limiting on only for tests that request this fixture (after Redis is up)."""
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    _flush_testclient_rate_keys()


def test_health_is_not_rate_limited(
    client: TestClient, enable_rate_limits: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "rate_limit_requests", 2)
    monkeypatch.setattr(settings, "rate_limit_window_seconds", 60)

    for _ in range(5):
        response = client.get("/health")
        assert response.status_code == 200


def test_default_policy_returns_429_with_retry_after(
    client: TestClient, enable_rate_limits: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "rate_limit_requests", 3)
    monkeypatch.setattr(settings, "rate_limit_window_seconds", 60)
    # Keep auth limit high so this exercises the default policy only.
    monkeypatch.setattr(settings, "rate_limit_auth_requests", 100)

    for _ in range(3):
        response = client.get("/openapi.json")
        assert response.status_code == 200

    blocked = client.get("/openapi.json")
    assert blocked.status_code == 429
    assert blocked.json() == {"detail": "Rate limit exceeded"}
    assert blocked.headers.get("Retry-After") == "60"


def test_auth_policy_is_stricter_than_default(
    client: TestClient, enable_rate_limits: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "rate_limit_requests", 100)
    monkeypatch.setattr(settings, "rate_limit_auth_requests", 2)
    monkeypatch.setattr(settings, "rate_limit_auth_window_seconds", 60)

    for _ in range(2):
        response = client.post(
            "/auth/login",
            data={"username": "nobody@example.com", "password": "wrong"},
        )
        # Credentials fail, but the request still counts toward the auth limit.
        assert response.status_code == 401

    blocked = client.post(
        "/auth/login",
        data={"username": "nobody@example.com", "password": "wrong"},
    )
    assert blocked.status_code == 429
    assert blocked.headers.get("Retry-After") == "60"
