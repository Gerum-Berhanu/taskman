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


def create_workspace(
    client: TestClient,
    headers: dict[str, str],
    name: str = "Engineering",
) -> dict:
    response = client.post(
        "/workspaces",
        json={"name": name},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def tasks_url(workspace_id: str, task_id: str | None = None) -> str:
    base = f"/workspaces/{workspace_id}/tasks"
    return f"{base}/{task_id}" if task_id else base


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

    assert duplicate.status_code == 409
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
    response = client.get(tasks_url(str(uuid4())))

    assert response.status_code == 401


def test_workspace_task_crud(client: TestClient) -> None:
    register(client)
    headers = login(client)
    workspace = create_workspace(client, headers)
    workspace_id = workspace["id"]

    created = client.post(
        tasks_url(workspace_id),
        json={"title": "First task", "description": "Test description"},
        headers=headers,
    )

    assert created.status_code == 201, created.text
    task = created.json()
    task_id = task["id"]
    assert UUID(task_id)
    assert task["title"] == "First task"
    assert task["status"] == "pending"
    assert task["workspace_id"] == workspace_id

    fetched = client.get(tasks_url(workspace_id, task_id), headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == task_id

    listed = client.get(tasks_url(workspace_id), headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    updated = client.patch(
        tasks_url(workspace_id, task_id),
        json={"title": "Updated task", "status": "completed"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated task"
    assert updated.json()["status"] == "completed"

    deleted = client.delete(tasks_url(workspace_id, task_id), headers=headers)
    assert deleted.status_code == 204
    assert deleted.content == b""

    missing = client.get(tasks_url(workspace_id, task_id), headers=headers)
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Task not found"


def test_missing_task_update_and_delete_return_not_found(
    client: TestClient,
) -> None:
    register(client)
    headers = login(client)
    workspace = create_workspace(client, headers)
    workspace_id = workspace["id"]
    missing_task_id = str(uuid4())

    updated = client.patch(
        tasks_url(workspace_id, missing_task_id),
        json={"title": "Does not exist"},
        headers=headers,
    )
    deleted = client.delete(
        tasks_url(workspace_id, missing_task_id),
        headers=headers,
    )

    assert updated.status_code == 404
    assert updated.json()["detail"] == "Task not found"
    assert deleted.status_code == 404
    assert deleted.json()["detail"] == "Task not found"


def test_viewer_cannot_create_or_delete_task(client: TestClient) -> None:
    register(client, email="owner@example.com")
    owner_headers = login(client, email="owner@example.com")
    workspace = create_workspace(client, owner_headers)
    workspace_id = workspace["id"]

    viewer = register(client, email="viewer@example.com")
    viewer_headers = login(client, email="viewer@example.com")

    added = client.post(
        f"/workspaces/{workspace_id}/members",
        json={"user_id": viewer["id"], "role": "viewer"},
        headers=owner_headers,
    )
    assert added.status_code == 201, added.text

    create_as_viewer = client.post(
        tasks_url(workspace_id),
        json={"title": "Nope"},
        headers=viewer_headers,
    )
    assert create_as_viewer.status_code == 403

    created = client.post(
        tasks_url(workspace_id),
        json={"title": "Owner task"},
        headers=owner_headers,
    )
    assert created.status_code == 201, created.text
    task_id = created.json()["id"]

    listed = client.get(tasks_url(workspace_id), headers=viewer_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    delete_as_viewer = client.delete(
        tasks_url(workspace_id, task_id),
        headers=viewer_headers,
    )
    assert delete_as_viewer.status_code == 403


def test_task_assignee_must_be_workspace_member(client: TestClient) -> None:
    owner = register(client, email="owner@example.com")
    owner_headers = login(client, email="owner@example.com")
    workspace = create_workspace(client, owner_headers)
    workspace_id = workspace["id"]

    outsider = register(client, email="outsider@example.com")
    member = register(client, email="member@example.com")

    added = client.post(
        f"/workspaces/{workspace_id}/members",
        json={"user_id": member["id"], "role": "editor"},
        headers=owner_headers,
    )
    assert added.status_code == 201, added.text

    missing_user = client.post(
        tasks_url(workspace_id),
        json={"title": "Bad user", "assigned_user_id": str(uuid4())},
        headers=owner_headers,
    )
    assert missing_user.status_code == 404
    assert missing_user.json()["detail"] == "User not found"

    non_member = client.post(
        tasks_url(workspace_id),
        json={"title": "Outsider", "assigned_user_id": outsider["id"]},
        headers=owner_headers,
    )
    assert non_member.status_code == 400
    assert non_member.json()["detail"] == "Assignee is not a member of the workspace"

    created = client.post(
        tasks_url(workspace_id),
        json={"title": "Assigned", "assigned_user_id": member["id"]},
        headers=owner_headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["assigned_user_id"] == member["id"]
    task_id = created.json()["id"]

    reassigned = client.patch(
        tasks_url(workspace_id, task_id),
        json={"assigned_user_id": owner["id"]},
        headers=owner_headers,
    )
    assert reassigned.status_code == 200
    assert reassigned.json()["assigned_user_id"] == owner["id"]

    cleared = client.patch(
        tasks_url(workspace_id, task_id),
        json={"assigned_user_id": None},
        headers=owner_headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["assigned_user_id"] is None

    # Existing task + non-member assignee → assignee error
    bad_assignee = client.patch(
        tasks_url(workspace_id, task_id),
        json={"assigned_user_id": outsider["id"]},
        headers=owner_headers,
    )
    assert bad_assignee.status_code == 400
    assert bad_assignee.json()["detail"] == "Assignee is not a member of the workspace"

    # Missing task + non-member assignee → not-found (exist check before assignee)
    missing_with_assignee = client.patch(
        tasks_url(workspace_id, str(uuid4())),
        json={"assigned_user_id": outsider["id"]},
        headers=owner_headers,
    )
    assert missing_with_assignee.status_code == 404
    assert missing_with_assignee.json()["detail"] == "Task not found"
