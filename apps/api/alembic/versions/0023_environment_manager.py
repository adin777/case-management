"""Add explicit environment manager membership flag."""

import sqlalchemy as sa

from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("environment_memberships") as batch:
        batch.add_column(sa.Column("is_environment_manager", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.create_index("ix_environment_memberships_is_environment_manager", ["is_environment_manager"])
    op.execute("""
        UPDATE environment_memberships SET is_environment_manager = 1
        WHERE role_id IN (SELECT id FROM roles WHERE code = 'environment_admin')
    """)


def downgrade() -> None:
    with op.batch_alter_table("environment_memberships") as batch:
        batch.drop_index("ix_environment_memberships_is_environment_manager")
        batch.drop_column("is_environment_manager")
