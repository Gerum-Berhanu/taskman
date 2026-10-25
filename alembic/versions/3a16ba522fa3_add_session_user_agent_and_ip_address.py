"""add session user_agent and ip_address

Revision ID: 3a16ba522fa3
Revises: 00c799f5666e
Create Date: 2026-10-25 19:12:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3a16ba522fa3"
down_revision: Union[str, Sequence[str], None] = "00c799f5666e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable UA/IP metadata columns on client_sessions."""
    with op.batch_alter_table("client_sessions") as batch_op:
        batch_op.add_column(
            sa.Column("user_agent", sa.String(length=512), nullable=True)
        )
        batch_op.add_column(
            sa.Column("ip_address", sa.String(length=45), nullable=True)
        )


def downgrade() -> None:
    """Drop UA/IP metadata columns."""
    with op.batch_alter_table("client_sessions") as batch_op:
        batch_op.drop_column("ip_address")
        batch_op.drop_column("user_agent")
