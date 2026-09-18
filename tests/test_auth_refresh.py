"""Refresh-token auth flow tests.

Run with: uv run pytest -q tests/test_auth_refresh.py
"""

from uuid import UUID

import jwt
from fastapi.testclient import TestClient

from app.core.config import settings
from tests.conftest import activate_user, deactivate_user, expire_session_for_refresh

PASSWORD = "password123"
INVALID_DETAIL = "Could not validate credentials"


def register(client: TestClient, email: str = "alice@example.com") -> dict:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 201, response.text
    return response.json()


def login_tokens(client: TestClient, email: str = "alice@example.com") -> dict:
    response = client.post(
        "/auth/login",
        data={"username": email, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    return body


def refresh(client: TestClient, refresh_token: str):
    return client.post("/auth/refresh", json={"refresh_token": refresh_token})


def logout(client: TestClient, refresh_token: str):
    return client.post("/auth/logout", json={"refresh_token": refresh_token})


def logout_all(client: TestClient, refresh_token: str):
    return client.post("/auth/logout-all", json={"refresh_token": refresh_token})


def auth_header(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def assert_unauthorized(response) -> None:
    assert response.status_code == 401, response.text
    assert response.json()["detail"] == INVALID_DETAIL
    assert response.headers.get("www-authenticate") == "Bearer"


def test_refresh_rotates_tokens(client: TestClient) -> None:
    register(client)
    tokens = login_tokens(client)
    old_refresh = tokens["refresh_token"]

    rotated = refresh(client, old_refresh)
    assert rotated.status_code == 200, rotated.text
    new_tokens = rotated.json()
    assert new_tokens["access_token"]
    assert new_tokens["refresh_token"]
    assert new_tokens["refresh_token"] != old_refresh
    assert new_tokens["token_type"] == "bearer"

    # New access token works
    me = client.get("/auth/me", headers=auth_header(new_tokens["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"

    # Old refresh is no longer active
    assert_unauthorized(refresh(client, old_refresh))


def test_refresh_reuse_revokes_session(client: TestClient) -> None:
    register(client)
    tokens = login_tokens(client)
    old_refresh = tokens["refresh_token"]

    rotated = refresh(client, old_refresh)
    assert rotated.status_code == 200, rotated.text
    new_refresh = rotated.json()["refresh_token"]

    # Presenting the old token after rotation = reuse → kill this session
    assert_unauthorized(refresh(client, old_refresh))

    # Previously valid successor is dead with the session
    assert_unauthorized(refresh(client, new_refresh))


def test_logout_revokes_session(client: TestClient) -> None:
    register(client)
    tokens = login_tokens(client)

    logged_out = logout(client, tokens["refresh_token"])
    assert logged_out.status_code == 204
    assert logged_out.content == b""

    assert_unauthorized(refresh(client, tokens["refresh_token"]))


def test_logout_reuse_revokes_session(client: TestClient) -> None:
    register(client)
    tokens = login_tokens(client)
    old_refresh = tokens["refresh_token"]

    rotated = refresh(client, old_refresh)
    assert rotated.status_code == 200, rotated.text
    new_refresh = rotated.json()["refresh_token"]

    # Logout with the retired token = reuse → kill this session
    assert_unauthorized(logout(client, old_refresh))

    # Previously valid successor is dead with the session
    assert_unauthorized(refresh(client, new_refresh))


def test_logout_all_revokes_every_session(client: TestClient) -> None:
    register(client)
    session_a = login_tokens(client)
    session_b = login_tokens(client)

    assert session_a["refresh_token"] != session_b["refresh_token"]

    response = logout_all(client, session_a["refresh_token"])
    assert response.status_code == 204
    assert response.content == b""

    assert_unauthorized(refresh(client, session_a["refresh_token"]))
    assert_unauthorized(refresh(client, session_b["refresh_token"]))


def test_logout_all_reuse_revokes_session(client: TestClient) -> None:
    register(client)
    tokens = login_tokens(client)
    old_refresh = tokens["refresh_token"]

    rotated = refresh(client, old_refresh)
    assert rotated.status_code == 200, rotated.text
    new_refresh = rotated.json()["refresh_token"]

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


def test_refresh_inactive_user_revokes_session(client: TestClient) -> None:
    user = register(client)
    user_id = UUID(user["id"])
    tokens = login_tokens(client)
    refresh_token = tokens["refresh_token"]

    deactivate_user(user_id)
    assert_unauthorized(refresh(client, refresh_token))

    # Session was revoked: even after reactivation the old refresh stays dead
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
