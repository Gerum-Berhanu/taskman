import csv
import io
from collections.abc import Sequence
from typing import Any

from app.repositories import TaskRecord

CSV_COLUMNS = (
    "id",
    "title",
    "description",
    "status",
    "due_date",
    "assigned_user_id",
    "created_at",
    "updated_at",
)


def _cell(value: Any) -> str:
    """Format one CSV cell: empty for None, ISO for datetimes, else str()."""
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def tasks_to_csv(rows: Sequence[TaskRecord]) -> str:
    """Serialize task rows to CSV text with a fixed column order."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        data = row.model_dump()
        writer.writerow({col: _cell(data.get(col)) for col in CSV_COLUMNS})
    return buf.getvalue()