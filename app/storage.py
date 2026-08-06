"""Temporary in-memory store. Replaced by the database in a later slice."""

from uuid import uuid4

from pydantic import UUID4


_tasks: dict[UUID4, dict] = {}

def create(data: dict) -> dict:
    task_id = uuid4()
    task = {"id": task_id, "status": "pending", **data}
    _tasks[task_id] = task
    return task


def get(task_id: UUID4) -> dict | None:
    return _tasks.get(task_id)


def list_all() -> list[dict]:
    return list(_tasks.values())


def update(task_id: UUID4, fields: dict) -> dict:
    task = _tasks[task_id]
    task.update(fields)
    return task


def delete(task_id: UUID4):
    del _tasks[task_id]