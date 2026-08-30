"""rename user and task tables to plural names

Revision ID: bb04b469e7be
Revises: 910aa264b0a5
Create Date: 2026-08-30 20:26:07.116496

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'bb04b469e7be'
down_revision: Union[str, Sequence[str], None] = '910aa264b0a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table("task", "tasks")
    op.rename_table("user", "users")


def downgrade() -> None:
    """Downgrade schema."""
    op.rename_table("tasks", "task")
    op.rename_table("users", "user")
