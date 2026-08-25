"""Task repository: protocol, in-memory, and SQL implementations."""

from typing import Protocol
from uuid import uuid4

from pydantic import UUID4
from sqlmodel import Session, select

from app.core import timeutils as tu
from app.database.models import Task
from app.repositories.records import TaskRecord


class TaskRepository(Protocol):
    def create(self, data: dict) -> TaskRecord: ...

    def get(self, task_id: UUID4) -> TaskRecord | None: ...

    def list_all(self) -> list[TaskRecord]: ...

    def update(self, task_id: UUID4, fields: dict) -> TaskRecord | None: ...

    def delete(self, task_id: UUID4) -> bool: ...


def _to_task_record(task: Task) -> TaskRecord:
    return TaskRecord(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        due_date=task.due_date,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


class InMemoryTaskRepository(TaskRepository):
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

    def update(self, task_id: UUID4, fields: dict) -> TaskRecord | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        if not fields:
            return task
        task.update(fields)
        task["updated_at"] = tu.utcnow()
        return task

    def delete(self, task_id: UUID4) -> bool:
        if task_id not in self._tasks:
            return False
        del self._tasks[task_id]
        return True


class SqlTaskRepository(TaskRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, data: dict) -> TaskRecord:
        task = Task(
            title=data["title"],
            description=data.get("description"),
            due_date=data.get("due_date"),
        )
        self._session.add(task)
        self._session.commit()
        self._session.refresh(task)
        return _to_task_record(task)

    def get(self, task_id: UUID4) -> TaskRecord | None:
        task = self._session.get(Task, task_id)
        if task is None:
            return None
        return _to_task_record(task)

    def list_all(self) -> list[TaskRecord]:
        tasks = self._session.exec(select(Task)).all()
        return [_to_task_record(task) for task in tasks]

    def update(self, task_id: UUID4, fields: dict) -> TaskRecord | None:
        task = self._session.get(Task, task_id)
        if task is None:
            return None
        if not fields:
            return _to_task_record(task)

        for key, value in fields.items():
            setattr(task, key, value)
        task.updated_at = tu.utcnow()

        self._session.add(task)
        self._session.commit()
        self._session.refresh(task)
        return _to_task_record(task)

    def delete(self, task_id: UUID4) -> bool:
        task = self._session.get(Task, task_id)
        if task is None:
            return False
        self._session.delete(task)
        self._session.commit()
        return True
