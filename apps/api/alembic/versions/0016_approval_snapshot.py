"""Persist approval actor display-name snapshots.

Revision ID: 0016
Revises: 0015
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("approval_tasks") as batch:
        batch.add_column(sa.Column("approver_name_snapshot", sa.String(length=200), nullable=True))
    op.execute("""UPDATE approval_tasks SET approver_name_snapshot =
        (SELECT display_name FROM users WHERE users.id = approval_tasks.approver_user_id)
        WHERE approver_name_snapshot IS NULL""")


def downgrade() -> None:
    with op.batch_alter_table("approval_tasks") as batch:
        batch.drop_column("approver_name_snapshot")
