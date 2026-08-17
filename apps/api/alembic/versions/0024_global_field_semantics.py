"""Add global-field semantic bindings and environment presentation configuration."""

import sqlalchemy as sa

from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("global_case_field_definitions") as batch:
        batch.add_column(sa.Column("semantic_binding", sa.String(80), nullable=True))
        batch.create_index("ix_global_case_field_definitions_semantic_binding", ["semantic_binding"])
    with op.batch_alter_table("environment_global_case_fields") as batch:
        batch.add_column(sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("show_on_create", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.add_column(sa.Column("show_on_edit", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_table("user_import_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))


def downgrade() -> None:
    op.drop_table("user_import_sessions")
    with op.batch_alter_table("environment_global_case_fields") as batch:
        batch.drop_column("show_on_edit")
        batch.drop_column("show_on_create")
        batch.drop_column("is_required")
    with op.batch_alter_table("global_case_field_definitions") as batch:
        batch.drop_index("ix_global_case_field_definitions_semantic_binding")
        batch.drop_column("semantic_binding")
