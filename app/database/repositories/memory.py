"""In-memory repository implementations. Replaced by SQLAlchemy in a later slice."""

from typing import Any
from uuid import uuid4

from pydantic import UUID4

from app.core import timeutils as tu


class InMemoryTaskRepository:
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


class InMemoryUserRepository:
    def __init__(self) -> None:
        self._users: dict[UUID4, dict] = {}

    def get_by_email(self, email: str) -> dict[str, Any] | None:
        for user in self._users.values():
            if user["email"] == email:
                return user
        return None

    def create(self, *, email: str, hashed_password: str) -> dict:
        user_id = uuid4()
        user = {
            "id": user_id,
            "email": email,
            "hashed_password": hashed_password,
            "is_active": True,
            "created_at": tu.utcnow(),
        }
        self._users[user_id] = user
        return user


task_repository = InMemoryTaskRepository()
user_repository = InMemoryUserRepository()
