"""Repository interfaces — persistence contracts for services."""

from typing import Protocol

from pydantic import UUID4

from app.database.records import TaskRecord, UserRecord


class TaskRepository(Protocol):
    def create(self, data: dict) -> TaskRecord: ...

    def get(self, task_id: UUID4) -> TaskRecord | None: ...

    def list_all(self) -> list[TaskRecord]: ...

    def update(self, task_id: UUID4, fields: dict) -> TaskRecord | None: ...

    def delete(self, task_id: UUID4) -> bool: ...


class UserRepository(Protocol):
    def get_by_email(self, email: str) -> UserRecord | None: ...

    def create(self, *, email: str, hashed_password: str) -> UserRecord: ...
