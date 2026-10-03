"""Task summary endpoint and Redis cache fail-open / hit behavior."""

from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from tests.test_api import (
    FORBIDDEN_DETAIL,
    create_workspace,
    login,
    register,
    tasks_url,
)


def summary_url(workspace_id: str) -> str:
    return f"/workspaces/{workspace_id}/tasks/summary"


def test_summary_empty_workspace(client: TestClient) -> None:
    register(client)
    headers = login(client)
    workspace = create_workspace(client, headers)

    response = client.get(summary_url(workspace["id"]), headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "workspace_id": workspace["id"],
        "total": 0,
        "pending": 0,
        "in_progress": 0,
        "completed": 0,
    }


def test_summary_counts_mixed_statuses(client: TestClient) -> None:
    register(client)
    headers = login(client)
    workspace_id = create_workspace(client, headers)["id"]

    pending = client.post(
        tasks_url(workspace_id),
        json={"title": "Pending one"},
        headers=headers,
    )
    assert pending.status_code == 201, pending.text

    pending_two = client.post(
        tasks_url(workspace_id),
        json={"title": "Pending two"},
        headers=headers,
    )
    assert pending_two.status_code == 201, pending_two.text

    in_progress = client.post(
        tasks_url(workspace_id),
        json={"title": "In progress"},
        headers=headers,
    )
    assert in_progress.status_code == 201, in_progress.text
    patched = client.patch(
        tasks_url(workspace_id, in_progress.json()["id"]),
        json={"status": "in_progress"},
        headers=headers,
    )
    assert patched.status_code == 200, patched.text

    completed = client.post(
        tasks_url(workspace_id),
        json={"title": "Done"},
        headers=headers,
    )
    assert completed.status_code == 201, completed.text
    done = client.patch(
        tasks_url(workspace_id, completed.json()["id"]),
        json={"status": "completed"},
        headers=headers,
    )
    assert done.status_code == 200, done.text

    response = client.get(summary_url(workspace_id), headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "workspace_id": workspace_id,
        "total": 4,
        "pending": 2,
        "in_progress": 1,
        "completed": 1,
    }


def test_summary_viewer_can_read_stranger_forbidden(client: TestClient) -> None:
    register(client, email="owner@example.com")
    owner_headers = login(client, email="owner@example.com")
    workspace_id = create_workspace(client, owner_headers)["id"]

    viewer = register(client, email="viewer@example.com")
    viewer_headers = login(client, email="viewer@example.com")
    added = client.post(
        f"/workspaces/{workspace_id}/members",
        json={"user_id": viewer["id"], "role": "viewer"},
        headers=owner_headers,
    )
    assert added.status_code == 201, added.text

    register(client, email="stranger@example.com")
    stranger_headers = login(client, email="stranger@example.com")

    as_viewer = client.get(summary_url(workspace_id), headers=viewer_headers)
    as_stranger = client.get(summary_url(workspace_id), headers=stranger_headers)
    as_stranger_missing = client.get(
        summary_url(str(uuid4())), headers=stranger_headers
    )

    assert as_viewer.status_code == 200
    assert as_stranger.status_code == 403
    assert as_stranger_missing.status_code == 403
    assert as_stranger.json()["detail"] == FORBIDDEN_DETAIL
    assert as_stranger.json() == as_stranger_missing.json()


def test_summary_tracks_create_update_delete(client: TestClient) -> None:
    register(client)
    headers = login(client)
    workspace_id = create_workspace(client, headers)["id"]

    empty = client.get(summary_url(workspace_id), headers=headers)
    assert empty.status_code == 200
    assert empty.json()["total"] == 0

    created = client.post(
        tasks_url(workspace_id),
        json={"title": "Track me"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    task_id = created.json()["id"]

    after_create = client.get(summary_url(workspace_id), headers=headers)
    assert after_create.status_code == 200
    assert after_create.json() == {
        "workspace_id": workspace_id,
        "total": 1,
        "pending": 1,
        "in_progress": 0,
        "completed": 0,
    }

    updated = client.patch(
        tasks_url(workspace_id, task_id),
        json={"status": "completed"},
        headers=headers,
    )
    assert updated.status_code == 200, updated.text

    after_update = client.get(summary_url(workspace_id), headers=headers)
    assert after_update.status_code == 200
    assert after_update.json()["completed"] == 1
    assert after_update.json()["pending"] == 0
    assert after_update.json()["total"] == 1

    deleted = client.delete(tasks_url(workspace_id, task_id), headers=headers)
    assert deleted.status_code == 204

    after_delete = client.get(summary_url(workspace_id), headers=headers)
    assert after_delete.status_code == 200
    assert after_delete.json()["total"] == 0


def test_summary_cache_hit_skips_db(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    register(client)
    headers = login(client)
    workspace_id = create_workspace(client, headers)["id"]

    cached = {
        "workspace_id": workspace_id,
        "total": 99,
        "pending": 99,
        "in_progress": 0,
        "completed": 0,
    }
    monkeypatch.setattr(
        "app.services.task.get_json",
        AsyncMock(return_value=cached),
    )
    set_mock = AsyncMock()
    monkeypatch.setattr("app.services.task.set_json", set_mock)

    response = client.get(summary_url(workspace_id), headers=headers)

    assert response.status_code == 200
    assert response.json() == cached
    set_mock.assert_not_called()


def test_summary_succeeds_when_cache_backend_errors(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    register(client)
    headers = login(client)
    workspace_id = create_workspace(client, headers)["id"]

    created = client.post(
        tasks_url(workspace_id),
        json={"title": "Still counted"},
        headers=headers,
    )
    assert created.status_code == 201, created.text

    monkeypatch.setattr(
        "app.services.task.get_json",
        AsyncMock(side_effect=RuntimeError("redis down")),
    )
    monkeypatch.setattr(
        "app.services.task.set_json",
        AsyncMock(side_effect=RuntimeError("redis down")),
    )

    response = client.get(summary_url(workspace_id), headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "workspace_id": workspace_id,
        "total": 1,
        "pending": 1,
        "in_progress": 0,
        "completed": 0,
    }


def test_mutation_calls_cache_invalidation(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    register(client)
    headers = login(client)
    workspace_id = create_workspace(client, headers)["id"]

    delete_mock = AsyncMock()
    monkeypatch.setattr("app.services.task.delete_keys", delete_mock)

    created = client.post(
        tasks_url(workspace_id),
        json={"title": "Invalidate me"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    task_id = created.json()["id"]

    assert delete_mock.await_count >= 1
    key = f"cache:ws:{workspace_id}:tasks:summary"
    assert any(key in call.args for call in delete_mock.await_args_list)

    delete_mock.reset_mock()
    patched = client.patch(
        tasks_url(workspace_id, task_id),
        json={"status": "completed"},
        headers=headers,
    )
    assert patched.status_code == 200, patched.text
    assert delete_mock.await_count >= 1

    delete_mock.reset_mock()
    deleted = client.delete(tasks_url(workspace_id, task_id), headers=headers)
    assert deleted.status_code == 204
    assert delete_mock.await_count >= 1
