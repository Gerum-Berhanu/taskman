"""drop client_sessions.revoked_at

Revision ID: 00c799f5666e
Revises: cb73738ce2dd
Create Date: 2026-10-25 15:31:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "00c799f5666e"
down_revision: Union[str, Sequence[str], None] = "cb73738ce2dd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Sessions end by delete; soft-revoke column is unused."""
    with op.batch_alter_table("client_sessions") as batch_op:
        batch_op.drop_column("revoked_at")


def downgrade() -> None:
    """Restore nullable revoked_at for soft-revoke."""
    with op.batch_alter_table("client_sessions") as batch_op:
        batch_op.add_column(
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True)
        )
