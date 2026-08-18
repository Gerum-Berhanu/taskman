"""In-memory repository implementations. Replaced by SQLAlchemy in a later slice."""

from uuid import uuid4

from pydantic import UUID4

from app.core import timeutils as tu
from app.database.records import TaskRecord, UserRecord


class InMemoryTaskRepository:
    def __init__(self) -> None:
        self._tasks: dict[UUID4, TaskRecord] = {}

    def create(self, data: dict) -> TaskRecord:
        task_id = uuid4()
        task: TaskRecord = {
            "id": task_id,
            "title": data["title"],
            "description": data.get("description"),
            "due_date": data.get("due_date"),
            "status": "pending",
            "created_at": tu.utcnow(),
            "updated_at": None,
        }
        self._tasks[task_id] = task
        return task

    def get(self, task_id: UUID4) -> TaskRecord | None:
        return self._tasks.get(task_id)

    def list_all(self) -> list[TaskRecord]:
        return list(self._tasks.values())

    def update(self, task_id: UUID4, fields: dict) -> TaskRecord:
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
        self._users: dict[UUID4, UserRecord] = {}

    def get_by_email(self, email: str) -> UserRecord | None:
        for user in self._users.values():
            if user["email"] == email:
                return user
        return None

    def create(self, *, email: str, hashed_password: str) -> UserRecord:
        user_id = uuid4()
        user: UserRecord = {
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
