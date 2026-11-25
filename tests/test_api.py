"""Run the suite anytime with
>> uv run pytest -q
"""

from unittest.mock import patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient


PASSWORD = "password123"
FIXED_OTP = "123456"


def start_register(
    client: TestClient,
    email: str = "alice@example.com",
    password: str = PASSWORD,
) -> dict:
    """POST /auth/register → 202 pending ticket (OTP generation patched)."""
    with (
        patch("app.services.user.generate_registration_otp", return_value=FIXED_OTP),
        patch(
            "app.workers.tasks.send_registration_otp_email",
            return_value="Your Taskman verification code",
        ),
    ):
        response = client.post(
            "/auth/register",
            json={"email": email, "password": password},
        )
    assert response.status_code == 202, response.text
    body = response.json()
    assert "registration_id" in body
    return body


def verify_register(
    client: TestClient,
    registration_id: str,
    otp: str = FIXED_OTP,
) -> dict:
    """POST /auth/register/verify → 201 user (welcome mail patched)."""
    with patch(
        "app.workers.tasks.send_welcome_email",
        return_value="Welcome to Taskman",
    ):
        response = client.post(
            "/auth/register/verify",
            json={"registration_id": registration_id, "otp": otp},
        )
    assert response.status_code == 201, response.text
    return response.json()


def register(client: TestClient, email: str = "alice@example.com") -> dict:
    """Full OTP registration for older tests that expect a created user."""
    pending = start_register(client, email=email)
    return verify_register(client, pending["registration_id"])


def login(client: TestClient, email: str = "alice@example.com") -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"email": email, "password": PASSWORD},
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


def post_tasks(
    client: TestClient,
    workspace_id: str,
    headers: dict[str, str],
    items: list[dict],
):
    """POST collection create with a JSON array of task bodies."""
    return client.post(tasks_url(workspace_id), json=items, headers=headers)


def delete_tasks(
    client: TestClient,
    workspace_id: str,
    headers: dict[str, str],
    task_ids: list[str],
):
    """DELETE collection with a JSON array of task ids."""
    return client.request(
        "DELETE",
        tasks_url(workspace_id),
        json=task_ids,
        headers=headers,
    )


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_and_reject_duplicate_email(client: TestClient) -> None:
    user = register(client)

    assert UUID(user["id"])
    assert user["email"] == "alice@example.com"
    assert user["detail"] == "User registered successfully"

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
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert set(body) == {"id", "email", "is_active", "created_at"}
    assert "hashed_password" not in body
    assert "password" not in body
    # Timezone-aware UTC (Z or +00:00), not a naive local timestamp
    assert body["created_at"].endswith("Z") or body["created_at"].endswith("+00:00")


def test_login_rejects_invalid_password(client: TestClient) -> None:
    register(client)

    response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "wrongpass"},
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


def test_list_workspaces_empty_when_none(client: TestClient) -> None:
    register(client)
    headers = login(client)

    response = client.get("/workspaces", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


def test_workspace_task_crud(client: TestClient) -> None:
    register(client)
    headers = login(client)
    workspace = create_workspace(client, headers)
    workspace_id = workspace["id"]

    created = post_tasks(
        client,
        workspace_id,
        headers,
        [{"title": "First task", "description": "Test description"}],
    )

    assert created.status_code == 201, created.text
    body = created.json()
    assert isinstance(body, list) and len(body) == 1
    task = body[0]
    task_id = task["id"]
    assert UUID(task_id)
    assert task["title"] == "First task"
    assert task["status"] == "pending"
    assert task["workspace_id"] == workspace_id
    assert task["updated_at"] is None

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
    assert updated.json()["updated_at"] is not None
    assert (
        updated.json()["updated_at"].endswith("Z")
        or updated.json()["updated_at"].endswith("+00:00")
    )

    deleted = delete_tasks(client, workspace_id, headers, [task_id])
    assert deleted.status_code == 204
    assert deleted.content == b""

    missing = client.get(tasks_url(workspace_id, task_id), headers=headers)
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Task not found"


def test_missing_task_update_404_delete_ignores_unknown(
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
    deleted = delete_tasks(client, workspace_id, headers, [missing_task_id])

    assert updated.status_code == 404
    assert updated.json()["detail"] == "Task not found"
    assert deleted.status_code == 204


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

    create_as_viewer = post_tasks(
        client, workspace_id, viewer_headers, [{"title": "Nope"}]
    )
    assert create_as_viewer.status_code == 403

    created = post_tasks(
        client, workspace_id, owner_headers, [{"title": "Owner task"}]
    )
    assert created.status_code == 201, created.text
    task_id = created.json()[0]["id"]

    listed = client.get(tasks_url(workspace_id), headers=viewer_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    delete_as_viewer = delete_tasks(
        client, workspace_id, viewer_headers, [task_id]
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

    missing_user = post_tasks(
        client,
        workspace_id,
        owner_headers,
        [{"title": "Bad user", "assigned_user_id": str(uuid4())}],
    )
    assert missing_user.status_code == 400
    assert missing_user.json()["detail"] == "Assignee is not a member of the workspace"

    non_member = post_tasks(
        client,
        workspace_id,
        owner_headers,
        [{"title": "Outsider", "assigned_user_id": outsider["id"]}],
    )
    assert non_member.status_code == 400
    assert non_member.json()["detail"] == "Assignee is not a member of the workspace"

    created = post_tasks(
        client,
        workspace_id,
        owner_headers,
        [{"title": "Assigned", "assigned_user_id": member["id"]}],
    )
    assert created.status_code == 201, created.text
    assert created.json()[0]["assigned_user_id"] == member["id"]
    task_id = created.json()[0]["id"]

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


FORBIDDEN_DETAIL = "Insufficient workspace permissions"


def test_workspace_access_errors_do_not_enumerate(client: TestClient) -> None:
    register(client, email="owner@example.com")
    owner_headers = login(client, email="owner@example.com")
    workspace = create_workspace(client, owner_headers)
    workspace_id = workspace["id"]
    missing_workspace_id = str(uuid4())

    register(client, email="stranger@example.com")
    stranger_headers = login(client, email="stranger@example.com")

    stranger_on_real = client.get(tasks_url(workspace_id), headers=stranger_headers)
    stranger_on_missing = client.get(
        tasks_url(missing_workspace_id), headers=stranger_headers
    )
    owner_on_missing = client.get(
        tasks_url(missing_workspace_id), headers=owner_headers
    )

    assert stranger_on_real.status_code == 403
    assert stranger_on_missing.status_code == 403
    assert owner_on_missing.status_code == 403
    assert stranger_on_real.json() == stranger_on_missing.json() == owner_on_missing.json()
    assert stranger_on_real.json()["detail"] == FORBIDDEN_DETAIL

    # Member + missing task still 404 (not an enumeration of workspaces)
    missing_task = client.get(
        tasks_url(workspace_id, str(uuid4())),
        headers=owner_headers,
    )
    assert missing_task.status_code == 404
    assert missing_task.json()["detail"] == "Task not found"


def test_reject_empty_workspace_name_and_task_title(client: TestClient) -> None:
    register(client)
    headers = login(client)

    empty_workspace = client.post(
        "/workspaces",
        json={"name": ""},
        headers=headers,
    )
    assert empty_workspace.status_code == 422

    workspace = create_workspace(client, headers)
    workspace_id = workspace["id"]

    empty_create = post_tasks(
        client, workspace_id, headers, [{"title": ""}]
    )
    assert empty_create.status_code == 422

    created = post_tasks(
        client, workspace_id, headers, [{"title": "Valid"}]
    )
    assert created.status_code == 201, created.text
    task_id = created.json()[0]["id"]

    empty_update = client.patch(
        tasks_url(workspace_id, task_id),
        json={"title": ""},
        headers=headers,
    )
    assert empty_update.status_code == 422


def test_reject_oversized_email_and_task_description(client: TestClient) -> None:
    # Valid-looking shape but over the 254-char cap (and EmailStr length rules).
    oversized_email = f"{'a' * 64}@{'b' * 200}.com"
    assert len(oversized_email) > 254

    rejected_register = client.post(
        "/auth/register",
        json={"email": oversized_email, "password": PASSWORD},
    )
    assert rejected_register.status_code == 422

    register(client)
    headers = login(client)
    workspace = create_workspace(client, headers)
    workspace_id = workspace["id"]

    rejected_create = post_tasks(
        client,
        workspace_id,
        headers,
        [{"title": "Ok", "description": "x" * 5001}],
    )
    assert rejected_create.status_code == 422

    created = post_tasks(
        client,
        workspace_id,
        headers,
        [{"title": "Ok", "description": "x" * 5000}],
    )
    assert created.status_code == 201, created.text
    task_id = created.json()[0]["id"]

    rejected_update = client.patch(
        tasks_url(workspace_id, task_id),
        json={"description": "y" * 5001},
        headers=headers,
    )
    assert rejected_update.status_code == 422


def test_list_create_multi_and_rejects_empty_or_bare_object(
    client: TestClient,
) -> None:
    register(client)
    headers = login(client)
    workspace_id = create_workspace(client, headers)["id"]

    multi = post_tasks(
        client,
        workspace_id,
        headers,
        [{"title": "A"}, {"title": "B"}],
    )
    assert multi.status_code == 201, multi.text
    assert len(multi.json()) == 2
    assert [t["title"] for t in multi.json()] == ["A", "B"]

    empty = post_tasks(client, workspace_id, headers, [])
    assert empty.status_code == 422

    bare = client.post(
        tasks_url(workspace_id),
        json={"title": "Bare"},
        headers=headers,
    )
    assert bare.status_code == 422


def test_list_create_over_max_rejected(client: TestClient) -> None:
    register(client)
    headers = login(client)
    workspace_id = create_workspace(client, headers)["id"]

    # TaskCreateBatch max_length uses settings.task_bulk_max_items (default 50).
    over = post_tasks(
        client,
        workspace_id,
        headers,
        [{"title": f"T{i}"} for i in range(51)],
    )
    assert over.status_code == 422


def test_list_create_bad_assignee_creates_none(client: TestClient) -> None:
    register(client, email="owner@example.com")
    headers = login(client, email="owner@example.com")
    workspace_id = create_workspace(client, headers)["id"]
    member = register(client, email="member@example.com")
    added = client.post(
        f"/workspaces/{workspace_id}/members",
        json={"user_id": member["id"], "role": "editor"},
        headers=headers,
    )
    assert added.status_code == 201, added.text

    before = client.get(tasks_url(workspace_id), headers=headers)
    assert before.status_code == 200
    assert before.json() == []

    rejected = post_tasks(
        client,
        workspace_id,
        headers,
        [
            {"title": "Ok", "assigned_user_id": member["id"]},
            {"title": "Bad", "assigned_user_id": str(uuid4())},
        ],
    )
    assert rejected.status_code == 400
    assert rejected.json()["detail"] == "Assignee is not a member of the workspace"

    after = client.get(tasks_url(workspace_id), headers=headers)
    assert after.status_code == 200
    assert after.json() == []


def test_list_delete_multi_and_ignores_unknown_ids(client: TestClient) -> None:
    register(client)
    headers = login(client)
    workspace_id = create_workspace(client, headers)["id"]

    created = post_tasks(
        client,
        workspace_id,
        headers,
        [{"title": "Keep-or-kill-1"}, {"title": "Keep-or-kill-2"}],
    )
    assert created.status_code == 201, created.text
    ids = [t["id"] for t in created.json()]

    deleted = delete_tasks(
        client, workspace_id, headers, [ids[0], str(uuid4()), ids[1]]
    )
    assert deleted.status_code == 204

    listed = client.get(tasks_url(workspace_id), headers=headers)
    assert listed.status_code == 200
    assert listed.json() == []

    again = delete_tasks(client, workspace_id, headers, [str(uuid4())])
    assert again.status_code == 204


def test_list_delete_empty_rejected_editor_forbidden(client: TestClient) -> None:
    register(client, email="owner@example.com")
    owner_headers = login(client, email="owner@example.com")
    workspace_id = create_workspace(client, owner_headers)["id"]

    editor = register(client, email="editor@example.com")
    editor_headers = login(client, email="editor@example.com")
    added = client.post(
        f"/workspaces/{workspace_id}/members",
        json={"user_id": editor["id"], "role": "editor"},
        headers=owner_headers,
    )
    assert added.status_code == 201, added.text

    created = post_tasks(
        client, workspace_id, owner_headers, [{"title": "Owned"}]
    )
    assert created.status_code == 201, created.text
    task_id = created.json()[0]["id"]

    empty = delete_tasks(client, workspace_id, owner_headers, [])
    assert empty.status_code == 422

    as_editor = delete_tasks(client, workspace_id, editor_headers, [task_id])
    assert as_editor.status_code == 403

    old_path = client.delete(tasks_url(workspace_id, task_id), headers=owner_headers)
    assert old_path.status_code in (404, 405)
