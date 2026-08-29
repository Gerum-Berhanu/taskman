"""Run the suite anytime with
>> uv run pytest -q
"""

from uuid import UUID, uuid4

from fastapi.testclient import TestClient


PASSWORD = "password123"


def register(client: TestClient, email: str = "alice@example.com") -> dict:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 201, response.text
    return response.json()


def login(client: TestClient, email: str = "alice@example.com") -> dict[str, str]:
    response = client.post(
        "/auth/login",
        data={"username": email, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_and_reject_duplicate_email(client: TestClient) -> None:
    user = register(client)

    assert UUID(user["id"])
    assert user["email"] == "alice@example.com"
    assert user["message"] == "User registered successfully"

    duplicate = client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": PASSWORD},
    )

    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "Account with this email already exists"


def test_login_and_read_current_user(client: TestClient) -> None:
    register(client)
    headers = login(client)

    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"
    assert "hashed_password" not in response.json()


def test_login_rejects_invalid_password(client: TestClient) -> None:
    register(client)

    response = client.post(
        "/auth/login",
        data={"username": "alice@example.com", "password": "wrongpass"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"
    assert response.headers["www-authenticate"] == "Bearer"


def test_current_user_rejects_invalid_token(client: TestClient) -> None:
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"
    assert response.headers["www-authenticate"] == "Bearer"


def test_protected_tasks_require_authentication(client: TestClient) -> None:
    response = client.get("/tasks")

    assert response.status_code == 401


def test_task_crud(client: TestClient) -> None:
    register(client)
    headers = login(client)

    created = client.post(
        "/tasks",
        json={"title": "First task", "description": "Test description"},
        headers=headers,
    )

    assert created.status_code == 201, created.text
    task = created.json()
    task_id = task["id"]
    assert UUID(task_id)
    assert task["title"] == "First task"
    assert task["status"] == "pending"

    fetched = client.get(f"/tasks/{task_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == task_id

    listed = client.get("/tasks", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    updated = client.patch(
        f"/tasks/{task_id}",
        json={"title": "Updated task", "status": "completed"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated task"
    assert updated.json()["status"] == "completed"

    deleted = client.delete(f"/tasks/{task_id}", headers=headers)
    assert deleted.status_code == 204
    assert deleted.content == b""

    missing = client.get(f"/tasks/{task_id}", headers=headers)
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Task not found"


def test_missing_task_update_and_delete_return_not_found(
    client: TestClient,
) -> None:
    register(client)
    headers = login(client)
    missing_task_id = uuid4()

    updated = client.patch(
        f"/tasks/{missing_task_id}",
        json={"title": "Does not exist"},
        headers=headers,
    )
    deleted = client.delete(f"/tasks/{missing_task_id}", headers=headers)

    assert updated.status_code == 404
    assert updated.json()["detail"] == "Task not found"
    assert deleted.status_code == 404
    assert deleted.json()["detail"] == "Task not found"
