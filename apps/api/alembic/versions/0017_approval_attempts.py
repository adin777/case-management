"""Persist explicit approval attempt numbers.

Revision ID: 0017
Revises: 0016
"""
import sqlalchemy as sa

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("approval_instances") as batch:
        batch.add_column(sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"))


def downgrade() -> None:
    with op.batch_alter_table("approval_instances") as batch:
        batch.drop_column("attempt_number")
