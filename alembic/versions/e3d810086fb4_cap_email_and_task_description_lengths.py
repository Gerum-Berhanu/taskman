"""cap email and task description lengths

Revision ID: e3d810086fb4
Revises: a8cfa429943e
Create Date: 2026-10-18 13:01:01.162628

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e3d810086fb4"
down_revision: Union[str, Sequence[str], None] = "a8cfa429943e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _dependent_views(bind, *, table: str, column: str) -> list[tuple[str, str, str]]:
    """Return (schema, view_name, view_def) for views that depend on table.column."""
    rows = bind.execute(
        sa.text(
            """
            SELECT DISTINCT
                n.nspname AS schema_name,
                c.relname AS view_name,
                pg_get_viewdef(c.oid, true) AS view_def
            FROM pg_depend d
            JOIN pg_rewrite r ON r.oid = d.objid
            JOIN pg_class c ON c.oid = r.ev_class
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_class t ON t.oid = d.refobjid
            JOIN pg_attribute a
              ON a.attrelid = d.refobjid AND a.attnum = d.refobjsubid
            WHERE c.relkind = 'v'
              AND t.relname = :table
              AND a.attname = :column
              AND a.attnum > 0
              AND NOT a.attisdropped
            ORDER BY n.nspname, c.relname
            """
        ),
        {"table": table, "column": column},
    ).all()
    return [(row.schema_name, row.view_name, row.view_def) for row in rows]


def _drop_views(views: list[tuple[str, str, str]]) -> None:
    for schema, name, _ in views:
        op.execute(sa.text(f'DROP VIEW IF EXISTS "{schema}"."{name}"'))


def _create_views(views: list[tuple[str, str, str]]) -> None:
    for schema, name, view_def in views:
        op.execute(
            sa.text(f'CREATE VIEW "{schema}"."{name}" AS {view_def}')
        )


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite ignores VARCHAR length and cannot ALTER COLUMN TYPE; API/model
    # max_length is enough there. Postgres gets real column type limits.
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    email_views = _dependent_views(bind, table="users", column="email")
    description_views = _dependent_views(bind, table="tasks", column="description")
    _drop_views(email_views + description_views)

    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(),
        type_=sa.String(length=254),
        existing_nullable=False,
    )
    op.alter_column(
        "tasks",
        "description",
        existing_type=sa.String(),
        type_=sa.String(length=5000),
        existing_nullable=True,
    )

    _create_views(description_views + email_views)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    email_views = _dependent_views(bind, table="users", column="email")
    description_views = _dependent_views(bind, table="tasks", column="description")
    _drop_views(email_views + description_views)

    op.alter_column(
        "tasks",
        "description",
        existing_type=sa.String(length=5000),
        type_=sa.String(),
        existing_nullable=True,
    )
    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(length=254),
        type_=sa.String(),
        existing_nullable=False,
    )

    _create_views(description_views + email_views)
