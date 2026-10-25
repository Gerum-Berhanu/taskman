"""Refresh-token auth flow tests (HttpOnly cookie).

Run with: uv run pytest -q tests/test_auth_refresh.py
"""

from uuid import UUID

import jwt
from fastapi.testclient import TestClient

from app.core.config import settings
from tests.conftest import activate_user, deactivate_user, expire_session_for_refresh

PASSWORD = "password123"
INVALID_DETAIL = "Could not validate credentials"
_REFRESH_COOKIE = settings.refresh_token_cookie_name
_DEVICE_COOKIE = settings.device_id_cookie_name


def register(client: TestClient, email: str = "alice@example.com") -> dict:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _httponly_cookie_value(response, cookie_name: str) -> str:
    """Assert Set-Cookie for cookie_name is present and HttpOnly; return its value."""
    prefix = f"{cookie_name}="
    headers = response.headers.get_list("set-cookie")
    matches = [h for h in headers if h.startswith(prefix)]
    assert matches, f"missing Set-Cookie for {cookie_name}: {headers}"
    header = matches[0]
    assert "HttpOnly" in header or "httponly" in header.lower(), header
    value = header.split(";", 1)[0].removeprefix(prefix)
    assert value, header
    return value


def assert_httponly_refresh_cookie(response) -> str:
    return _httponly_cookie_value(response, _REFRESH_COOKIE)


def assert_httponly_device_cookie(response) -> str:
    return _httponly_cookie_value(response, _DEVICE_COOKIE)


def clear_device_cookie(client: TestClient) -> None:
    """Drop device_id so the next login mints a new install identity."""
    client.cookies.delete(_DEVICE_COOKIE)


def login_tokens(client: TestClient, email: str = "alice@example.com") -> dict:
    response = client.post(
        "/auth/login",
        data={"username": email, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert "refresh_token" not in body
    refresh_token = assert_httponly_refresh_cookie(response)
    device_id = assert_httponly_device_cookie(response)
    # Keep jar in sync for the next request (TestClient + HttpOnly can be flaky).
    client.cookies.set(_REFRESH_COOKIE, refresh_token)
    client.cookies.set(_DEVICE_COOKIE, device_id)
    return {
        "access_token": body["access_token"],
        "token_type": body["token_type"],
        "refresh_token": refresh_token,
        "device_id": device_id,
    }


def _use_refresh_cookie(client: TestClient, refresh_token: str | None) -> None:
    """Point the client jar at a specific refresh cookie (or leave jar as-is)."""
    if refresh_token is not None:
        client.cookies.set(_REFRESH_COOKIE, refresh_token)


def refresh(client: TestClient, refresh_token: str | None = None):
    _use_refresh_cookie(client, refresh_token)
    return client.post("/auth/refresh")


def logout(client: TestClient, refresh_token: str | None = None):
    _use_refresh_cookie(client, refresh_token)
    return client.post("/auth/logout")


def logout_all(client: TestClient, refresh_token: str | None = None):
    _use_refresh_cookie(client, refresh_token)
    return client.post("/auth/logout-all")


def list_sessions(client: TestClient, access_token: str):
    return client.get("/auth/sessions", headers=auth_header(access_token))


def auth_header(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def assert_unauthorized(response) -> None:
    assert response.status_code == 401, response.text
    assert response.json()["detail"] == INVALID_DETAIL
    assert response.headers.get("www-authenticate") == "Bearer"


def test_login_sets_httponly_refresh_and_device_cookies(client: TestClient) -> None:
    register(client)
    tokens = login_tokens(client)
    assert tokens["refresh_token"]
    assert tokens["access_token"]
    assert tokens["device_id"]


def test_refresh_without_cookie_is_unauthorized(client: TestClient) -> None:
    register(client)
    login_tokens(client)
    client.cookies.clear()
    assert_unauthorized(refresh(client))


def test_refresh_rotates_tokens(client: TestClient) -> None:
    register(client)
    tokens = login_tokens(client)
    old_refresh = tokens["refresh_token"]

    rotated = refresh(client, old_refresh)
    assert rotated.status_code == 200, rotated.text
    new_body = rotated.json()
    assert new_body["access_token"]
    assert "refresh_token" not in new_body
    assert new_body["token_type"] == "bearer"
    new_refresh = assert_httponly_refresh_cookie(rotated)
    assert new_refresh != old_refresh

    # New access token works
    me = client.get("/auth/me", headers=auth_header(new_body["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"

    # Old refresh is no longer active
    assert_unauthorized(refresh(client, old_refresh))


def test_refresh_reuse_deletes_session(client: TestClient) -> None:
    register(client)
    tokens = login_tokens(client)
    old_refresh = tokens["refresh_token"]

    rotated = refresh(client, old_refresh)
    assert rotated.status_code == 200, rotated.text
    new_refresh = assert_httponly_refresh_cookie(rotated)

    # Presenting the old token after rotation = reuse → kill this session
    assert_unauthorized(refresh(client, old_refresh))

    # Previously valid successor is dead with the session
    assert_unauthorized(refresh(client, new_refresh))


def test_logout_deletes_session(client: TestClient) -> None:
    register(client)
    tokens = login_tokens(client)

    logged_out = logout(client, tokens["refresh_token"])
    assert logged_out.status_code == 204
    assert logged_out.content == b""

    assert_unauthorized(refresh(client, tokens["refresh_token"]))


def test_logout_reuse_deletes_session(client: TestClient) -> None:
    register(client)
    tokens = login_tokens(client)
    old_refresh = tokens["refresh_token"]

    rotated = refresh(client, old_refresh)
    assert rotated.status_code == 200, rotated.text
    new_refresh = assert_httponly_refresh_cookie(rotated)

    # Logout with the retired token = reuse → kill this session
    assert_unauthorized(logout(client, old_refresh))

    # Previously valid successor is dead with the session
    assert_unauthorized(refresh(client, new_refresh))


def test_logout_all_deletes_every_session(client: TestClient) -> None:
    register(client)
    session_a = login_tokens(client)
    clear_device_cookie(client)
    session_b = login_tokens(client)

    assert session_a["refresh_token"] != session_b["refresh_token"]
    assert session_a["device_id"] != session_b["device_id"]

    response = logout_all(client, session_a["refresh_token"])
    assert response.status_code == 204
    assert response.content == b""

    assert_unauthorized(refresh(client, session_a["refresh_token"]))
    assert_unauthorized(refresh(client, session_b["refresh_token"]))


def test_logout_all_reuse_deletes_session(client: TestClient) -> None:
    register(client)
    tokens = login_tokens(client)
    old_refresh = tokens["refresh_token"]

    rotated = refresh(client, old_refresh)
    assert rotated.status_code == 200, rotated.text
    new_refresh = assert_httponly_refresh_cookie(rotated)

    clear_device_cookie(client)
    other_session = login_tokens(client)

    # Logout-all with the retired token = reuse → kill this session only
    assert_unauthorized(logout_all(client, old_refresh))
    assert_unauthorized(refresh(client, new_refresh))

    # Other live sessions are untouched (parity with single-session reuse)
    still_ok = refresh(client, other_session["refresh_token"])
    assert still_ok.status_code == 200, still_ok.text


def test_refresh_rejects_malformed_token(client: TestClient) -> None:
    register(client)
    assert_unauthorized(refresh(client, "not-a-valid-refresh-token"))
    assert_unauthorized(refresh(client, "not-a-uuid.still-invalid"))


def test_refresh_rejects_expired_session(client: TestClient) -> None:
    register(client)
    tokens = login_tokens(client)
    expire_session_for_refresh(tokens["refresh_token"])
    assert_unauthorized(refresh(client, tokens["refresh_token"]))


def test_inactive_user_cannot_login_refresh_or_use_access(
    client: TestClient,
) -> None:
    user = register(client)
    tokens = login_tokens(client)

    deactivate_user(UUID(user["id"]))

    # Login blocked (same message as bad credentials)
    login_response = client.post(
        "/auth/login",
        data={"username": "alice@example.com", "password": PASSWORD},
    )
    assert login_response.status_code == 401
    assert login_response.json()["detail"] == "Incorrect email or password"

    # Refresh blocked
    assert_unauthorized(refresh(client, tokens["refresh_token"]))

    # Existing access token blocked on protected routes
    assert_unauthorized(
        client.get("/auth/me", headers=auth_header(tokens["access_token"]))
    )


def test_refresh_inactive_user_deletes_session(client: TestClient) -> None:
    user = register(client)
    user_id = UUID(user["id"])
    tokens = login_tokens(client)
    refresh_token = tokens["refresh_token"]

    deactivate_user(user_id)
    assert_unauthorized(refresh(client, refresh_token))

    # Session was deleted: even after reactivation the old refresh stays dead
    activate_user(user_id)
    assert_unauthorized(refresh(client, refresh_token))


def test_access_rejects_invalid_jwt_sub(client: TestClient) -> None:
    register(client)
    tokens = login_tokens(client)

    # Well-formed JWT but non-UUID subject must not crash the dependency
    bad_access = jwt.encode(
        {"sub": "not-a-uuid", "exp": 9_999_999_999},
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    assert_unauthorized(client.get("/auth/me", headers=auth_header(bad_access)))
    assert_unauthorized(
        client.get("/auth/me", headers=auth_header(tokens["access_token"] + "x"))
    )


def test_relogin_same_device_replaces_session(client: TestClient) -> None:
    register(client)
    first = login_tokens(client)
    second = login_tokens(client)

    assert first["device_id"] == second["device_id"]
    assert first["refresh_token"] != second["refresh_token"]
    assert_unauthorized(refresh(client, first["refresh_token"]))
    assert refresh(client, second["refresh_token"]).status_code == 200


def test_cleared_device_cookie_allows_parallel_sessions(client: TestClient) -> None:
    register(client)
    first = login_tokens(client)
    clear_device_cookie(client)
    second = login_tokens(client)

    assert first["device_id"] != second["device_id"]
    assert refresh(client, first["refresh_token"]).status_code == 200
    assert refresh(client, second["refresh_token"]).status_code == 200


def test_refresh_ignores_missing_or_wrong_device_cookie(client: TestClient) -> None:
    register(client)
    tokens = login_tokens(client)

    clear_device_cookie(client)
    without_device = refresh(client, tokens["refresh_token"])
    assert without_device.status_code == 200, without_device.text
    rotated = assert_httponly_refresh_cookie(without_device)

    client.cookies.set(_DEVICE_COOKIE, "00000000-0000-0000-0000-000000000000")
    assert refresh(client, rotated).status_code == 200


def test_logout_clears_refresh_but_keeps_device_cookie(client: TestClient) -> None:
    register(client)
    tokens = login_tokens(client)
    device_before = tokens["device_id"]

    logged_out = logout(client, tokens["refresh_token"])
    assert logged_out.status_code == 204
    # Logout must not clear device_id (cookie may still be in the jar).
    client.cookies.set(_DEVICE_COOKIE, device_before)

    again = login_tokens(client)
    assert again["device_id"] == device_before
    assert_unauthorized(refresh(client, tokens["refresh_token"]))


def test_list_sessions_requires_auth(client: TestClient) -> None:
    response = client.get("/auth/sessions")
    assert response.status_code == 401
    # HTTPBearer missing-credentials detail (not InvalidTokenError).
    assert response.json()["detail"] == "Not authenticated"


def test_list_sessions_marks_current_and_stores_metadata(client: TestClient) -> None:
    register(client)
    client.headers["User-Agent"] = "taskman-test-agent/1.0"
    first = login_tokens(client)
    clear_device_cookie(client)
    second = login_tokens(client)

    listed = list_sessions(client, second["access_token"])
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert len(body) == 2

    by_device = {row["device_id"]: row for row in body}
    assert by_device[second["device_id"]]["is_current"] is True
    assert by_device[first["device_id"]]["is_current"] is False
    for row in body:
        assert row["user_agent"] == "taskman-test-agent/1.0"
        assert row["ip_address"]
