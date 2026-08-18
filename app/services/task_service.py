from pydantic import UUID4

from app.database.records import TaskRecord
from app.database.repositories.protocols import TaskRepository
from app.models.task import TaskCreate, TaskUpdate


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
        return self._repository.update(task_id, data.model_dump(exclude_unset=True))

    def delete(self, task_id: UUID4) -> None:
        self._repository.delete(task_id)
