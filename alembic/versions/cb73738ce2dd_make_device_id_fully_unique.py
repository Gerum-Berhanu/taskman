"""make device_id fully unique

Revision ID: cb73738ce2dd
Revises: b7e4c1a92f0d
Create Date: 2026-10-25 14:35:22.588919

"""

from collections import defaultdict
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "cb73738ce2dd"
down_revision: Union[str, Sequence[str], None] = "b7e4c1a92f0d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PARTIAL_INDEX = "uq_client_sessions_user_device_active"
_DEVICE_UNIQUE = "uq_client_sessions_device_id"
_WHERE_ACTIVE = sa.text("revoked_at IS NULL")


def _dedupe_device_ids() -> None:
    """Keep one row per device_id (prefer active, then newest created_at)."""
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, device_id, revoked_at, created_at FROM client_sessions"
        )
    ).fetchall()

    by_device: dict[object, list] = defaultdict(list)
    for row_id, device_id, revoked_at, created_at in rows:
        by_device[device_id].append((row_id, revoked_at, created_at))

    for sessions in by_device.values():
        if len(sessions) <= 1:
            continue
        # Prefer active (revoked_at IS NULL), then newest created_at.
        keep_id = min(
            sessions,
            key=lambda s: (s[1] is not None, -s[2].timestamp()),
        )[0]
        for row_id, _, _ in sessions:
            if row_id == keep_id:
                continue
            bind.execute(
                sa.text("DELETE FROM client_sessions WHERE id = :id"),
                {"id": row_id},
            )


def upgrade() -> None:
    """Drop partial (user_id, device_id) unique; enforce global unique device_id."""
    _dedupe_device_ids()

    op.drop_index(
        _PARTIAL_INDEX,
        table_name="client_sessions",
        postgresql_where=_WHERE_ACTIVE,
        sqlite_where=_WHERE_ACTIVE,
    )

    with op.batch_alter_table("client_sessions") as batch_op:
        batch_op.create_unique_constraint(_DEVICE_UNIQUE, ["device_id"])


def downgrade() -> None:
    """Restore partial unique index on active (user_id, device_id)."""
    with op.batch_alter_table("client_sessions") as batch_op:
        batch_op.drop_constraint(_DEVICE_UNIQUE, type_="unique")

    op.create_index(
        _PARTIAL_INDEX,
        "client_sessions",
        ["user_id", "device_id"],
        unique=True,
        postgresql_where=_WHERE_ACTIVE,
        sqlite_where=_WHERE_ACTIVE,
    )
