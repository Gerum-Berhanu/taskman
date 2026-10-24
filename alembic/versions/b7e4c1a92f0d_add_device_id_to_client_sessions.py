"""add device_id to client_sessions with partial unique index

Revision ID: b7e4c1a92f0d
Revises: e3d810086fb4
Create Date: 2026-10-24 21:27:00.000000

"""

from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision: str = "b7e4c1a92f0d"
down_revision: Union[str, Sequence[str], None] = "e3d810086fb4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX = "uq_client_sessions_user_device_active"
_WHERE_ACTIVE = sa.text("revoked_at IS NULL")


def upgrade() -> None:
    """Add device_id, backfill, NOT NULL, then partial unique (user_id, device_id)."""
    with op.batch_alter_table("client_sessions") as batch_op:
        batch_op.add_column(sa.Column("device_id", sa.Uuid(), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id FROM client_sessions WHERE device_id IS NULL")
    ).fetchall()
    for (session_id,) in rows:
        bind.execute(
            sa.text(
                "UPDATE client_sessions SET device_id = :device_id WHERE id = :id"
            ),
            {"device_id": uuid4(), "id": session_id},
        )

    with op.batch_alter_table("client_sessions") as batch_op:
        batch_op.alter_column("device_id", existing_type=sa.Uuid(), nullable=False)

    op.create_index(
        _INDEX,
        "client_sessions",
        ["user_id", "device_id"],
        unique=True,
        postgresql_where=_WHERE_ACTIVE,
        sqlite_where=_WHERE_ACTIVE,
    )


def downgrade() -> None:
    """Drop partial unique index and device_id column."""
    op.drop_index(_INDEX, table_name="client_sessions")
    with op.batch_alter_table("client_sessions") as batch_op:
        batch_op.drop_column("device_id")
