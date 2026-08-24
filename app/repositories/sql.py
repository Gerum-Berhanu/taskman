"""SQLModel repository implementations."""

from pydantic import UUID4
from sqlmodel import Session, select

from app.core import timeutils as tu
from app.database.models import Task, User
from app.repositories.protocols import TaskRepository, UserRepository
from app.repositories.records import TaskRecord, UserRecord


def _to_task_record(task: Task) -> TaskRecord:
    """From raw ORM to service usable dict"""
    return TaskRecord(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        due_date=task.due_date,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _to_user_record(user: User) -> UserRecord:
    """From raw ORM to service usable dict"""
    return UserRecord(
        id=user.id,
        email=user.email,
        hashed_password=user.hashed_password,
        is_active=user.is_active,
        created_at=user.created_at,
    )


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


class SqlUserRepository(UserRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_email(self, email: str) -> UserRecord | None:
        statement = select(User).where(User.email == email)
        user = self._session.exec(statement).first()
        if user is None:
            return None
        return _to_user_record(user)

    def create(self, *, email: str, hashed_password: str) -> UserRecord:
        user = User(email=email, hashed_password=hashed_password)
        self._session.add(user)
        self._session.commit()
        self._session.refresh(user)
        return _to_user_record(user)
