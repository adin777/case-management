"""Add semantic workflow status categories.

Revision ID: 0011
Revises: 0010
"""

import sqlalchemy as sa

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_statuses",
        sa.Column("semantic_category", sa.String(length=30), nullable=False, server_default="open"),
    )
    op.execute("UPDATE workflow_statuses SET semantic_category = 'closed' WHERE is_closed = 1")
    op.execute("UPDATE workflow_statuses SET semantic_category = 'resolved' WHERE is_final = 1 AND is_closed = 0")
    op.add_column(
        "field_definitions",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.execute("UPDATE field_definitions SET is_active = 0 WHERE key IN ('location', 'device_type', 'details')")


def downgrade() -> None:
    op.drop_column("field_definitions", "is_active")
    op.drop_column("workflow_statuses", "semantic_category")
