"""Allow core-only cases without a dynamic form.

Revision ID: 0014
Revises: 0013
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("cases") as batch:
        batch.alter_column(
            "form_definition_id",
            existing_type=sa.Uuid(),
            nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("cases") as batch:
        batch.alter_column(
            "form_definition_id",
            existing_type=sa.Uuid(),
            nullable=False,
        )
