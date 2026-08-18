from typing import Any

from pydantic import UUID4

from app.database.stores import TaskStore
from app.models.task import TaskCreate, TaskUpdate


class TaskService:
    def __init__(self, store: TaskStore) -> None:
        self._store = store

    def create(self, data: TaskCreate) -> dict[str, Any]:
        return self._store.create(data.model_dump())

    def get(self, task_id: UUID4) -> dict[str, Any] | None:
        return self._store.get(task_id)

    def list_all(self) -> list[dict[str, Any]]:
        return self._store.list_all()

    def update(self, task_id: UUID4, data: TaskUpdate) -> dict[str, Any]:
        return self._store.update(task_id, data.model_dump(exclude_unset=True))

    def delete(self, task_id: UUID4) -> None:
        self._store.delete(task_id)
