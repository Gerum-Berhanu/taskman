"""Persistence record shapes for in-memory storage.

TypedDict describes the keys and value types of each stored row. At runtime
these are still plain dicts, but the type checker can catch typos like
task["titl"] or access to fields that do not exist on the record.
"""

from datetime import datetime
from typing import TypedDict

from pydantic import UUID4


class TaskRecord(TypedDict):
    id: UUID4
    title: str
    description: str | None
    status: str
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime | None


class UserRecord(TypedDict):
    id: UUID4
    email: str
    hashed_password: str
    is_active: bool
    created_at: datetime
