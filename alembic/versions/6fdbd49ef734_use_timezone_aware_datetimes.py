"""use_timezone_aware_datetimes

Revision ID: 6fdbd49ef734
Revises: 54eb18441699
Create Date: 2026-09-18 16:38:35.016172

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6fdbd49ef734"
down_revision: Union[str, Sequence[str], None] = "54eb18441699"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table, column, nullable)
_DATETIME_COLUMNS: tuple[tuple[str, str, bool], ...] = (
    ("users", "created_at", False),
    ("tasks", "created_at", False),
    ("tasks", "updated_at", True),
    ("tasks", "due_date", True),
    ("workspaces", "created_at", False),
    ("workspace_members", "joined_at", False),
    ("client_sessions", "created_at", False),
    ("client_sessions", "revoked_at", True),
    ("client_sessions", "rotated_at", True),
    ("client_sessions", "expires_at", False),
    ("refresh_tokens", "created_at", False),
)


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite has no TIMESTAMP WITH TIME ZONE; model metadata is enough there.
    # Postgres needs an explicit type change before aware UTC values land.
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for table, column, nullable in _DATETIME_COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(),
            type_=sa.DateTime(timezone=True),
            existing_nullable=nullable,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for table, column, nullable in _DATETIME_COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(timezone=True),
            type_=sa.DateTime(),
            existing_nullable=nullable,
            postgresql_using=f"{column} AT TIME ZONE",
        )
