"""Add case-insensitive group-name uniqueness."""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ux_groups_name_ci", "groups", [sa.text("lower(name)")], unique=True)


def downgrade() -> None:
    op.drop_index("ux_groups_name_ci", table_name="groups")
