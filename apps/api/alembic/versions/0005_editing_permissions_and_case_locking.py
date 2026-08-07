"""Add editable governance state and case locking.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("roles") as batch:
        batch.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    with op.batch_alter_table("permissions") as batch:
        batch.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    with op.batch_alter_table("cases") as batch:
        batch.add_column(sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("locked_by", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("lock_reason", sa.Text(), nullable=True))
        batch.create_foreign_key("fk_cases_locked_by_users", "users", ["locked_by"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("cases") as batch:
        batch.drop_constraint("fk_cases_locked_by_users", type_="foreignkey")
        batch.drop_column("lock_reason")
        batch.drop_column("locked_by")
        batch.drop_column("locked_at")
        batch.drop_column("is_locked")
    with op.batch_alter_table("permissions") as batch:
        batch.drop_column("is_active")
    with op.batch_alter_table("roles") as batch:
        batch.drop_column("is_active")
