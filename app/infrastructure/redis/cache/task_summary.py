"""Task-summary cache key helper."""

from uuid import UUID


def task_summary_key(workspace_id: UUID) -> str:
    return f"cache:ws:{workspace_id}:tasks:summary"
