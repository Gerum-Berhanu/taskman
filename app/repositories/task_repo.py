"""Task repository: protocol, in-memory, and SQL implementations."""

from typing import Protocol
from uuid import uuid4

from pydantic import UUID4
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core import timeutils as tu
from app.database.models import Task
from app.repositories.records import TaskRecord


class TaskRepository(Protocol):
    async def create(self, data: dict) -> TaskRecord: ...

    async def get(self, task_id: UUID4) -> TaskRecord | None: ...

    async def list_all(self) -> list[TaskRecord]: ...

    async def update(self, task_id: UUID4, fields: dict) -> TaskRecord | None: ...

    async def delete(self, task_id: UUID4) -> bool: ...


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

    async def create(self, data: dict) -> TaskRecord:
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

    async def get(self, task_id: UUID4) -> TaskRecord | None:
        return self._tasks.get(task_id)

    async def list_all(self) -> list[TaskRecord]:
        return list(self._tasks.values())

    async def update(self, task_id: UUID4, fields: dict) -> TaskRecord | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        if not fields:
            return task
        task.update(fields)
        task["updated_at"] = tu.utcnow()
        return task

    async def delete(self, task_id: UUID4) -> bool:
        if task_id not in self._tasks:
            return False
        del self._tasks[task_id]
        return True


class SqlTaskRepository(TaskRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: dict) -> TaskRecord:
        task = Task(
            title=data["title"],
            description=data.get("description"),
            due_date=data.get("due_date"),
        )
        self._session.add(task) 
        # add() only places the object in the session’s in-memory unit of work, so it is not awaitable.
        await self._session.commit()
        await self._session.refresh(task)
        return _to_task_record(task)

    async def get(self, task_id: UUID4) -> TaskRecord | None:
        task = await self._session.get(Task, task_id)
        if task is None:
            return None
        return _to_task_record(task)

    async def list_all(self) -> list[TaskRecord]:
        result = await self._session.exec(select(Task))
        tasks = result.all()
        # .exec() performs asynchronous database I/O, so it requires await. 
        # Methods such as .first() and .all() operate on the already-loaded result and are synchronous.
        return [_to_task_record(task) for task in tasks]

    async def update(self, task_id: UUID4, fields: dict) -> TaskRecord | None:
        task = await self._session.get(Task, task_id)
        if task is None:
            return None
        if not fields:
            return _to_task_record(task)

        for key, value in fields.items():
            setattr(task, key, value)
        task.updated_at = tu.utcnow()

        self._session.add(task)
        await self._session.commit()
        await self._session.refresh(task)
        return _to_task_record(task)

    async def delete(self, task_id: UUID4) -> bool:
        task = await self._session.get(Task, task_id)
        if task is None:
            return False
        await self._session.delete(task)
        await self._session.commit()
        return True
