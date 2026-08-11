"""Temporary in-memory store. Replaced by the database in a later slice."""

from uuid import uuid4

from pydantic import UUID4

import app.timeutils as tu


class TaskStore:
    def __init__(self) -> None:
        self._tasks: dict[UUID4, dict] = {}

    def create(self, data: dict) -> dict:
        task_id = uuid4()
        task = {
            **data,
            "id": task_id,
            "status": "pending",
            "created_at": tu.utcnow(),
            "updated_at": None,
        }
        self._tasks[task_id] = task
        return task

    def get(self, task_id: UUID4) -> dict | None:
        return self._tasks.get(task_id)

    def list_all(self) -> list[dict]:
        return list(self._tasks.values())

    def update(self, task_id: UUID4, fields: dict) -> dict:
        task = self._tasks[task_id]
        if not fields:
            return task
        task.update(fields)
        task["updated_at"] = tu.utcnow()
        return task

    def delete(self, task_id: UUID4) -> None:
        del self._tasks[task_id]


task_store = TaskStore()  # singleton for process lifetime