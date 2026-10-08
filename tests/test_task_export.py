"""Task CSV export accept path and CSV builder tests (no real SMTP)."""

import csv
import io
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.export.tasks_csv import CSV_COLUMNS, tasks_to_csv
from app.dto.repository import TaskRecord
from tests.test_api import (
    FORBIDDEN_DETAIL,
    create_workspace,
    login,
    register,
)


def export_url(workspace_id: str) -> str:
    return f"/workspaces/{workspace_id}/tasks/export"


def test_tasks_to_csv_header_and_null_cells() -> None:
    task_id = uuid4()
    workspace_id = uuid4()
    created = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)

    row = TaskRecord(
        id=task_id,
        title="Export me",
        description=None,
        status="pending",
        due_date=None,
        workspace_id=workspace_id,
        assigned_user_id=None,
        created_at=created,
        updated_at=None,
    )

    text = tasks_to_csv([row])
    reader = csv.DictReader(io.StringIO(text))

    assert reader.fieldnames == list(CSV_COLUMNS)
    parsed = next(reader)
    assert parsed["id"] == str(task_id)
    assert parsed["title"] == "Export me"
    assert parsed["description"] == ""
    assert parsed["status"] == "pending"
    assert parsed["due_date"] == ""
    assert parsed["assigned_user_id"] == ""
    assert parsed["created_at"] == created.isoformat()
    assert parsed["updated_at"] == ""


def test_export_requires_authentication(client: TestClient) -> None:
    workspace_id = str(uuid4())
    response = client.post(export_url(workspace_id))

    assert response.status_code == 401


def test_export_stranger_gets_forbidden(client: TestClient) -> None:
    register(client, email="owner@example.com")
    owner_headers = login(client, email="owner@example.com")
    workspace_id = create_workspace(client, owner_headers)["id"]

    register(client, email="stranger@example.com")
    stranger_headers = login(client, email="stranger@example.com")

    response = client.post(export_url(workspace_id), headers=stranger_headers)

    assert response.status_code == 403
    assert response.json()["detail"] == FORBIDDEN_DETAIL


def test_export_viewer_accepted_and_schedules_worker(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
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

    scheduled: list[tuple[str, str, str | None]] = []

    async def fake_run(
        *, workspace_id, to_email: str, actor_id: str | None = None
    ) -> None:
        scheduled.append((str(workspace_id), to_email, actor_id))

    monkeypatch.setattr("app.services.task.run_tasks_export", fake_run)

    response = client.post(export_url(workspace_id), headers=viewer_headers)

    assert response.status_code == 202
    assert response.content == b""
    assert len(scheduled) == 1
    assert scheduled[0][0] == workspace_id
    assert scheduled[0][1] == "viewer@example.com"
    assert scheduled[0][2] is not None
