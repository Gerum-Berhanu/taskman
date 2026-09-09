"""add refresh tokens and client sessions models and drop user sessions model

Revision ID: 2d3892c2a8cc
Revises: cd29eb0708c8
Create Date: 2026-09-10 00:28:47.621305

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = "2d3892c2a8cc"
down_revision: Union[str, Sequence[str], None] = "cd29eb0708c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1) Session table first — column present, FK to refresh_tokens deferred (circular).
    op.create_table(
        "client_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("active_token_id", sa.Uuid(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("rotated_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("active_token_id"),
    )
    op.create_index(
        op.f("ix_client_sessions_user_id"), "client_sessions", ["user_id"], unique=False
    )

    # 2) Token rows can now reference sessions.
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("client_session_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["client_session_id"], ["client_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        op.f("ix_refresh_tokens_client_session_id"),
        "refresh_tokens",
        ["client_session_id"],
        unique=False,
    )

    # 3) Close the circle: active pointer → refresh_tokens.
    # batch_alter_table recreates the table on SQLite (no ADD CONSTRAINT support).
    with op.batch_alter_table("client_sessions") as batch_op:
        batch_op.create_foreign_key(
            "fk_client_sessions_active_token_id_refresh_tokens",
            "refresh_tokens",
            ["active_token_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.drop_index(op.f("ix_user_sessions_user_id"), table_name="user_sessions")
    op.drop_table("user_sessions")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.CHAR(length=32), nullable=False),
        sa.Column("created_at", sa.DATETIME(), nullable=False),
        sa.Column("user_id", sa.CHAR(length=32), nullable=False),
        sa.Column("active_token_hash", sa.VARCHAR(), nullable=False),
        sa.Column("used_token_hashes", sqlite.JSON(), nullable=False),
        sa.Column("is_revoked", sa.BOOLEAN(), nullable=False),
        sa.Column("expires_at", sa.DATETIME(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("active_token_hash"),
    )
    op.create_index(
        op.f("ix_user_sessions_user_id"), "user_sessions", ["user_id"], unique=False
    )

    with op.batch_alter_table("client_sessions") as batch_op:
        batch_op.drop_constraint(
            "fk_client_sessions_active_token_id_refresh_tokens",
            type_="foreignkey",
        )
    op.drop_index(
        op.f("ix_refresh_tokens_client_session_id"), table_name="refresh_tokens"
    )
    op.drop_table("refresh_tokens")
    op.drop_index(op.f("ix_client_sessions_user_id"), table_name="client_sessions")
    op.drop_table("client_sessions")
