"""Add dynamic global fields and stable admin-group semantics.

Revision ID: 0022
Revises: 0021
"""
import sqlalchemy as sa

from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("groups") as batch:
        batch.add_column(sa.Column("is_system_admin_group", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.create_index("ix_groups_is_system_admin_group", ["is_system_admin_group"])
    op.execute(sa.text("""
        UPDATE groups SET is_system_admin_group = 1
        WHERE id IN (
          SELECT DISTINCT gm.group_id FROM group_members gm
          JOIN users u ON u.id = gm.user_id WHERE u.is_system_admin = 1
        )
    """))
    op.create_table(
        "global_case_field_definitions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("key", sa.String(80), nullable=False, unique=True),
        sa.Column("label_he", sa.String(200), nullable=False),
        sa.Column("label_en", sa.String(200), nullable=False, server_default=""),
        sa.Column("field_type", sa.String(40), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("configuration_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "environment_global_case_fields",
        sa.Column("environment_id", sa.Uuid(), sa.ForeignKey("environments.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("global_field_id", sa.Uuid(), sa.ForeignKey("global_case_field_definitions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "global_case_field_values",
        sa.Column("case_id", sa.Uuid(), sa.ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("global_field_id", sa.Uuid(), sa.ForeignKey("global_case_field_definitions.id"), primary_key=True),
        sa.Column("value_json", sa.JSON(), nullable=True),
    )
    # Legacy global catalogs are no longer active configuration. Cases retain their IDs/history.
    op.execute(sa.text("UPDATE global_status_definitions SET is_active = 0, is_initial = 0"))
    op.execute(sa.text("UPDATE global_priority_definitions SET is_active = 0"))
    op.execute(sa.text("UPDATE global_sub_priority_definitions SET is_active = 0"))


def downgrade() -> None:
    op.drop_table("global_case_field_values")
    op.drop_table("environment_global_case_fields")
    op.drop_table("global_case_field_definitions")
    with op.batch_alter_table("groups") as batch:
        batch.drop_index("ix_groups_is_system_admin_group")
        batch.drop_column("is_system_admin_group")
