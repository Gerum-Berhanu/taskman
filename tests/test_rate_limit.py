"""Scoped dependency rate-limit tests; suite keeps RATE_LIMIT_ENABLED=false."""

import pytest
from fastapi.params import Depends as DependsParam
from fastapi.testclient import TestClient
from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.core.config import settings
from app.infrastructure.redis.rate_limit import HITTERS
from app.dependencies import (
    AuthLoginLimit,
    AuthLogoutLimit,
    DomainExportLimit,
    DomainWriteLimit,
)
from tests.test_api import create_workspace, login, register, tasks_url
from tests.test_auth_refresh import login_tokens, logout, logout_all, refresh


def _dep_instance(dep: DependsParam):
    """Return the Require*Limit instance wrapped by Depends(...)."""
    return dep.dependency


def _flush_rate_limit_keys() -> None:
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        keys = list(client.scan_iter(match="rl:*"))
        if keys:
            client.delete(*keys)
    finally:
        client.close()


@pytest.fixture
def enable_rate_limits(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Turn limiting on only for tests that request this fixture (after Redis is up)."""
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    _flush_rate_limit_keys()


def _assert_rate_limited(response) -> None:
    assert response.status_code == 429, response.text
    assert response.json() == {"detail": "Too many requests"}
    retry_after = response.headers.get("Retry-After")
    assert retry_after is not None
    assert float(retry_after) >= 1


def test_health_is_not_rate_limited(
    client: TestClient, enable_rate_limits: None
) -> None:
    for _ in range(5):
        response = client.get("/health")
        assert response.status_code == 200


def test_auth_login_returns_429_with_retry_after(
    client: TestClient, enable_rate_limits: None
) -> None:
    # leaky_bucket: first hit allowed, second within the gap is denied.
    first = client.post(
        "/auth/login",
        data={"username": "nobody@example.com", "password": "wrong"},
    )
    assert first.status_code == 401

    blocked = client.post(
        "/auth/login",
        data={"username": "nobody@example.com", "password": "wrong"},
    )
    _assert_rate_limited(blocked)


def test_auth_register_and_refresh_do_not_share_login_counter(
    client: TestClient, enable_rate_limits: None
) -> None:
    # Burn auth.login; auth.register is a different Redis key.
    assert (
        client.post(
            "/auth/login",
            data={"username": "nobody@example.com", "password": "wrong"},
        ).status_code
        == 401
    )
    _assert_rate_limited(
        client.post(
            "/auth/login",
            data={"username": "nobody@example.com", "password": "wrong"},
        )
    )

    registered = client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "password123"},
    )
    assert registered.status_code == 201, registered.text

    # Fresh counters so login_tokens can succeed; then prove refresh != login.
    _flush_rate_limit_keys()
    tokens = login_tokens(client, email="alice@example.com")
    _assert_rate_limited(
        client.post(
            "/auth/login",
            data={"username": "alice@example.com", "password": "wrong"},
        )
    )
    refreshed = refresh(client, tokens["refresh_token"])
    assert refreshed.status_code == 200, refreshed.text


def test_auth_logout_shared_by_logout_and_logout_all(
    client: TestClient,
    enable_rate_limits: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_dep_instance(AuthLogoutLimit), "limit", 2)

    register(client, email="alice@example.com")
    tokens = login_tokens(client, email="alice@example.com")
    _flush_rate_limit_keys()

    assert logout(client, tokens["refresh_token"]).status_code == 204
    # Second hit shares auth.logout whether or not the token is still valid.
    assert logout_all(client, tokens["refresh_token"]).status_code in {204, 401}

    blocked = logout(client, tokens["refresh_token"])
    _assert_rate_limited(blocked)


def test_domain_write_routes_share_budget(
    client: TestClient,
    enable_rate_limits: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_dep_instance(DomainWriteLimit), "limit", 2)

    register(client)
    headers = login(client)
    _flush_rate_limit_keys()

    workspace = create_workspace(client, headers)
    created = client.post(
        tasks_url(workspace["id"]),
        json={"title": "One"},
        headers=headers,
    )
    assert created.status_code == 201, created.text

    blocked = client.post(
        tasks_url(workspace["id"]),
        json={"title": "Two"},
        headers=headers,
    )
    _assert_rate_limited(blocked)


def test_domain_read_separate_from_domain_write(
    client: TestClient,
    enable_rate_limits: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_dep_instance(DomainWriteLimit), "limit", 1)

    register(client)
    headers = login(client)
    _flush_rate_limit_keys()

    workspace = create_workspace(client, headers)
    blocked_write = client.post(
        tasks_url(workspace["id"]),
        json={"title": "Blocked"},
        headers=headers,
    )
    _assert_rate_limited(blocked_write)

    listed = client.get("/workspaces", headers=headers)
    assert listed.status_code == 200, listed.text


def test_domain_export_separate_from_domain_write(
    client: TestClient,
    enable_rate_limits: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_dep_instance(DomainWriteLimit), "limit", 1)
    monkeypatch.setattr(_dep_instance(DomainExportLimit), "limit", 1)

    async def fake_run(*, workspace_id, to_email: str, actor_id: str | None = None) -> None:
        return None

    monkeypatch.setattr("app.services.task.run_tasks_export", fake_run)

    register(client)
    headers = login(client)
    _flush_rate_limit_keys()

    workspace = create_workspace(client, headers)

    blocked_write = client.post(
        tasks_url(workspace["id"]),
        json={"title": "Blocked"},
        headers=headers,
    )
    _assert_rate_limited(blocked_write)

    # Export uses domain.export, not domain.write.
    first = client.post(
        f"/workspaces/{workspace['id']}/tasks/export",
        headers=headers,
    )
    assert first.status_code == 202, first.text

    blocked_export = client.post(
        f"/workspaces/{workspace['id']}/tasks/export",
        headers=headers,
    )
    _assert_rate_limited(blocked_export)


def test_kill_switch_disables_limits(
    client: TestClient,
    enable_rate_limits: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "rate_limit_enabled", False)

    for _ in range(5):
        response = client.post(
            "/auth/login",
            data={"username": "nobody@example.com", "password": "wrong"},
        )
        assert response.status_code == 401


def test_fail_open_when_hit_raises(
    client: TestClient,
    enable_rate_limits: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    algorithm = _dep_instance(AuthLoginLimit).algorithm

    async def boom(**_kwargs):
        raise RedisConnectionError("redis down")

    monkeypatch.setattr(HITTERS[algorithm], "hit", boom)

    response = client.post(
        "/auth/login",
        data={"username": "nobody@example.com", "password": "wrong"},
    )
    assert response.status_code == 401


def test_non_backend_errors_are_not_swallowed(
    client: TestClient,
    enable_rate_limits: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    algorithm = _dep_instance(AuthLoginLimit).algorithm

    async def boom(**_kwargs):
        raise ValueError("programmer error")

    monkeypatch.setattr(HITTERS[algorithm], "hit", boom)

    with pytest.raises(ValueError, match="programmer error"):
        client.post(
            "/auth/login",
            data={"username": "nobody@example.com", "password": "wrong"},
        )
