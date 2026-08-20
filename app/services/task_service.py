from pydantic import UUID4

from app.core.exceptions import TaskNotFoundError
from app.database.records import TaskRecord
from app.database.repositories.protocols import TaskRepository
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    def create(self, data: TaskCreate) -> TaskRecord:
        return self._repository.create(data.model_dump())

    def get(self, task_id: UUID4) -> TaskRecord | None:
        return self._repository.get(task_id)

    def list_all(self) -> list[TaskRecord]:
        return self._repository.list_all()

    def update(self, task_id: UUID4, data: TaskUpdate) -> TaskRecord:
        task = self._repository.update(task_id, data.model_dump(exclude_unset=True))
        if task is None:
            raise TaskNotFoundError
        return task

    def delete(self, task_id: UUID4) -> None:
        if not self._repository.delete(task_id):
            raise TaskNotFoundError
