"""Deactivate populated legacy demo fields without deleting values.

Revision ID: 0012
Revises: 0011
"""

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE field_definitions SET is_active = 0 "
        "WHERE key IN ('location', 'device_type', 'details', 'urgency')"
    )


def downgrade() -> None:
    op.execute("UPDATE field_definitions SET is_active = 1 WHERE key = 'urgency'")
