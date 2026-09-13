"""Add configurable field history and clear legacy audit rows.

Revision ID: 0033
Revises: 0032
"""
import sqlalchemy as sa

from alembic import op

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("field_definitions") as batch:
        batch.add_column(sa.Column("track_history", sa.Boolean(), nullable=False, server_default=sa.false()))
    with op.batch_alter_table("global_case_field_definitions") as batch:
        batch.add_column(sa.Column("track_history", sa.Boolean(), nullable=False, server_default=sa.false()))
    with op.batch_alter_table("case_field_definitions") as batch:
        batch.add_column(sa.Column("track_history", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table("system_settings", sa.Column("key", sa.String(100), primary_key=True), sa.Column("value_json", sa.JSON()))
    op.create_table("system_field_settings", sa.Column("field_key", sa.String(100), primary_key=True), sa.Column("track_history", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table(
        "case_field_change_history",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("case_id", sa.Uuid(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("environment_id", sa.Uuid(), sa.ForeignKey("environments.id"), nullable=False),
        sa.Column("field_scope", sa.String(30), nullable=False),
        sa.Column("field_definition_id", sa.Uuid()), sa.Column("semantic_binding", sa.String(80)),
        sa.Column("field_key", sa.String(100), nullable=False), sa.Column("field_label_snapshot", sa.String(200), nullable=False),
        sa.Column("old_value_json", sa.JSON()), sa.Column("new_value_json", sa.JSON()),
        sa.Column("old_display_value", sa.Text()), sa.Column("new_display_value", sa.Text()),
        sa.Column("changed_by", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("changed_by_name_snapshot", sa.String(200)),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("real_actor_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("effective_user_id", sa.Uuid(), sa.ForeignKey("users.id")),
    )
    for column in ("case_id", "environment_id", "field_definition_id", "changed_at"):
        op.create_index(f"ix_case_field_change_history_{column}", "case_field_change_history", [column])
    op.bulk_insert(sa.table("system_settings", sa.column("key", sa.String), sa.column("value_json", sa.JSON)), [{"key":"field_history_enabled","value_json":True}])
    op.execute(sa.text("DELETE FROM audit_events"))


def downgrade() -> None:
    op.drop_table("case_field_change_history")
    op.drop_table("system_field_settings")
    op.drop_table("system_settings")
    with op.batch_alter_table("global_case_field_definitions") as batch: batch.drop_column("track_history")
    with op.batch_alter_table("case_field_definitions") as batch: batch.drop_column("track_history")
    with op.batch_alter_table("field_definitions") as batch: batch.drop_column("track_history")
