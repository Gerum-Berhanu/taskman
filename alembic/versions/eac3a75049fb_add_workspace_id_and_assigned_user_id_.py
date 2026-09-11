"""add workspace_id and assigned_user_id to task model

Revision ID: eac3a75049fb
Revises: 1a99a051167b
Create Date: 2026-09-11 20:35:07.365925

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "eac3a75049fb"
down_revision: Union[str, Sequence[str], None] = "1a99a051167b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Existing tasks have no workspace to attach to; drop them before NOT NULL FK.
    op.execute(sa.text("DELETE FROM tasks"))

    # SQLite: ADD COLUMN ... NOT NULL fails without a non-NULL default;
    # batch_alter_table recreates the table (also needed for FKs).
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(sa.Column("workspace_id", sa.Uuid(), nullable=False))
        batch_op.add_column(sa.Column("assigned_user_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_tasks_workspace_id_workspaces",
            "workspaces",
            ["workspace_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            "fk_tasks_assigned_user_id_users",
            "users",
            ["assigned_user_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_constraint("fk_tasks_assigned_user_id_users", type_="foreignkey")
        batch_op.drop_constraint("fk_tasks_workspace_id_workspaces", type_="foreignkey")
        batch_op.drop_column("assigned_user_id")
        batch_op.drop_column("workspace_id")
