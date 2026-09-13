"""Allow transfer history for cases without a status.

Revision ID: 0034
Revises: 0033
"""
import sqlalchemy as sa

from alembic import op

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("case_transfer_histories") as batch:
        batch.alter_column("from_status_id", existing_type=sa.Uuid(), nullable=True)
        batch.alter_column("to_status_id", existing_type=sa.Uuid(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("case_transfer_histories") as batch:
        batch.alter_column("to_status_id", existing_type=sa.Uuid(), nullable=False)
