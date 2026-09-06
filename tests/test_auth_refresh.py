"""Refresh-token auth flow tests.

Run with: uv run pytest -q tests/test_auth_refresh.py
"""

from fastapi.testclient import TestClient

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


def test_refresh_reuse_revokes_family(client: TestClient) -> None:
    register(client)
    tokens = login_tokens(client)
    old_refresh = tokens["refresh_token"]

    rotated = refresh(client, old_refresh)
    assert rotated.status_code == 200, rotated.text
    new_refresh = rotated.json()["refresh_token"]

    # Presenting the old token after rotation = reuse
    assert_unauthorized(refresh(client, old_refresh))

    # Family is revoked: the previously valid new token also fails
    assert_unauthorized(refresh(client, new_refresh))


def test_logout_revokes_session(client: TestClient) -> None:
    register(client)
    tokens = login_tokens(client)

    logged_out = logout(client, tokens["refresh_token"])
    assert logged_out.status_code == 204
    assert logged_out.content == b""

    assert_unauthorized(refresh(client, tokens["refresh_token"]))


def test_logout_all_revokes_every_session(client: TestClient) -> None:
    register(client)
    session_a = login_tokens(client)
    session_b = login_tokens(client)

    assert session_a["refresh_token"] != session_b["refresh_token"]

    response = client.post(
        "/auth/logout-all",
        headers=auth_header(session_a["access_token"]),
    )
    assert response.status_code == 204
    assert response.content == b""

    assert_unauthorized(refresh(client, session_a["refresh_token"]))
    assert_unauthorized(refresh(client, session_b["refresh_token"]))


def test_refresh_rejects_malformed_token(client: TestClient) -> None:
    register(client)
    assert_unauthorized(refresh(client, "not-a-valid-refresh-token"))
    assert_unauthorized(refresh(client, "not-a-uuid.still-invalid"))
