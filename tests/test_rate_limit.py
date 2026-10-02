"""Rate-limit tests opt in via monkeypatch; suite keeps RATE_LIMIT_ENABLED=false."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from redis import Redis
from starlette.requests import Request

import app.core.rate_limit_policies as rate_limit_policies
from app.core.config import settings
from app.core.rate_limit_policies import (
    AUTH_POLICY,
    DEFAULT_POLICY,
    TASK_READS_POLICY,
    TASK_WRITES_POLICY,
    RateLimitPolicy,
)
from app.http.dependencies.rate_limit import rate_limit
from app.http.rate_limit import get_explicit_route_policy_name


def _flush_testclient_rate_keys() -> None:
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        keys = list(client.scan_iter(match="rl_sliding_window_counter:*:testclient"))
        if keys:
            client.delete(*keys)
    finally:
        client.close()


def _policy_registry(
    *,
    default_limit: int,
    auth_limit: int,
    task_reads_limit: int,
    task_writes_limit: int,
    window_seconds: int = 60,
) -> dict[str, RateLimitPolicy]:
    return {
        DEFAULT_POLICY: RateLimitPolicy(DEFAULT_POLICY, default_limit, window_seconds),
        AUTH_POLICY: RateLimitPolicy(AUTH_POLICY, auth_limit, window_seconds),
        TASK_READS_POLICY: RateLimitPolicy(TASK_READS_POLICY, task_reads_limit, window_seconds),
        TASK_WRITES_POLICY: RateLimitPolicy(TASK_WRITES_POLICY, task_writes_limit, window_seconds),
    }


def _prepare_task_context(client: TestClient) -> tuple[dict[str, str], str, str]:
    email = "owner@example.com"
    password = "password123"

    created = client.post("/auth/register", json={"email": email, "password": password})
    assert created.status_code == 201, created.text

    login_response = client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 200, login_response.text
    token = login_response.json()["access_token"]
    headers = {"Authorization": "Bearer " + token}

    workspace_response = client.post(
        "/workspaces",
        json={"name": "Engineering"},
        headers=headers,
    )
    assert workspace_response.status_code == 201, workspace_response.text
    workspace_id = workspace_response.json()["id"]

    task_response = client.post(
        f"/workspaces/{workspace_id}/tasks",
        json={"title": "First task"},
        headers=headers,
    )
    assert task_response.status_code == 201, task_response.text
    task_id = task_response.json()["id"]
    return headers, workspace_id, task_id


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
    monkeypatch.setattr(
        rate_limit_policies,
        "get_rate_limit_policies",
        lambda: _policy_registry(
            default_limit=2,
            auth_limit=100,
            task_reads_limit=100,
            task_writes_limit=100,
        ),
    )

    for _ in range(5):
        response = client.get("/health")
        assert response.status_code == 200


def test_default_policy_returns_429_with_retry_after(
    client: TestClient, enable_rate_limits: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        rate_limit_policies,
        "get_rate_limit_policies",
        lambda: _policy_registry(
            default_limit=3,
            auth_limit=100,
            task_reads_limit=100,
            task_writes_limit=100,
        ),
    )

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
    monkeypatch.setattr(
        rate_limit_policies,
        "get_rate_limit_policies",
        lambda: _policy_registry(
            default_limit=100,
            auth_limit=2,
            task_reads_limit=100,
            task_writes_limit=100,
        ),
    )

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


def test_task_read_and_write_policies_are_enforced(
    client: TestClient, enable_rate_limits: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers, workspace_id, task_id = _prepare_task_context(client)
    _flush_testclient_rate_keys()
    monkeypatch.setattr(
        rate_limit_policies,
        "get_rate_limit_policies",
        lambda: _policy_registry(
            default_limit=100,
            auth_limit=100,
            task_reads_limit=1,
            task_writes_limit=2,
        ),
    )

    first_read = client.get(f"/workspaces/{workspace_id}/tasks/{task_id}", headers=headers)
    assert first_read.status_code == 200
    blocked_read = client.get(f"/workspaces/{workspace_id}/tasks/{task_id}", headers=headers)
    assert blocked_read.status_code == 429
    assert blocked_read.headers.get("Retry-After") == "60"

    _flush_testclient_rate_keys()
    first_write = client.patch(
        f"/workspaces/{workspace_id}/tasks/{task_id}",
        json={"title": "Updated once"},
        headers=headers,
    )
    assert first_write.status_code == 200
    second_write = client.patch(
        f"/workspaces/{workspace_id}/tasks/{task_id}",
        json={"title": "Updated twice"},
        headers=headers,
    )
    assert second_write.status_code == 200
    blocked_write = client.patch(
        f"/workspaces/{workspace_id}/tasks/{task_id}",
        json={"title": "Blocked"},
        headers=headers,
    )
    assert blocked_write.status_code == 429
    assert blocked_write.headers.get("Retry-After") == "60"


def test_explicit_task_policy_routes_skip_middleware_fallback(
    client: TestClient, enable_rate_limits: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers, workspace_id, task_id = _prepare_task_context(client)
    _flush_testclient_rate_keys()
    monkeypatch.setattr(
        rate_limit_policies,
        "get_rate_limit_policies",
        lambda: _policy_registry(
            default_limit=0,
            auth_limit=100,
            task_reads_limit=2,
            task_writes_limit=100,
        ),
    )

    first = client.get(f"/workspaces/{workspace_id}/tasks/{task_id}", headers=headers)
    second = client.get(f"/workspaces/{workspace_id}/tasks/{task_id}", headers=headers)
    blocked = client.get(f"/workspaces/{workspace_id}/tasks/{task_id}", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert blocked.status_code == 429


def test_policy_registry_can_be_monkeypatched(
    client: TestClient, enable_rate_limits: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        rate_limit_policies,
        "get_rate_limit_policies",
        lambda: _policy_registry(
            default_limit=1,
            auth_limit=100,
            task_reads_limit=100,
            task_writes_limit=100,
        ),
    )

    first = client.get("/openapi.json")
    second = client.get("/openapi.json")
    assert first.status_code == 200
    assert second.status_code == 429


def test_fail_open_when_rate_limit_backend_errors(
    client: TestClient, enable_rate_limits: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _raise_backend_error(*args, **kwargs):
        raise RuntimeError("Redis unavailable")

    monkeypatch.setattr("app.http.rate_limit.hit_sliding_window_counter", _raise_backend_error)
    middleware_fallback_response = client.get("/openapi.json")
    assert middleware_fallback_response.status_code == 200

    headers, workspace_id, task_id = _prepare_task_context(client)
    route_policy_response = client.get(
        f"/workspaces/{workspace_id}/tasks/{task_id}",
        headers=headers,
    )
    assert route_policy_response.status_code == 200


def test_explicit_policy_found_when_earlier_full_match_has_none() -> None:
    """Param routes can FULL-match before a more specific route with a policy."""
    app = FastAPI()

    @app.get("/items/{item_id}")
    async def by_id(item_id: str) -> dict[str, str]:
        return {"item_id": item_id}

    @app.get("/items/special", dependencies=[rate_limit(AUTH_POLICY)])
    async def special() -> dict[str, bool]:
        return {"special": True}

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/items/special",
        "raw_path": b"/items/special",
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "app": app,
    }
    request = Request(scope)

    assert get_explicit_route_policy_name(request) == AUTH_POLICY
