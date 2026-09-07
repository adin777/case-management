"""Add complete SLA lifecycle state.

Revision ID: 0031
Revises: 0030
"""
import sqlalchemy as sa

from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("sla_policies") as batch:
        batch.add_column(sa.Column("priority_option_id", sa.Uuid()))
        batch.add_column(sa.Column("conditions_json", sa.JSON(), nullable=False, server_default="{}"))
        batch.add_column(sa.Column("pause_rules_json", sa.JSON(), nullable=False, server_default="{}"))
        batch.add_column(sa.Column("notification_json", sa.JSON(), nullable=False, server_default="{}"))
        batch.add_column(sa.Column("precedence", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("recalculate_on_change", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table("business_calendars", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("environment_id", sa.Uuid(), sa.ForeignKey("environments.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(200), nullable=False), sa.Column("timezone", sa.String(80), nullable=False), sa.Column("schedule_json", sa.JSON(), nullable=False), sa.Column("holidays_json", sa.JSON(), nullable=False), sa.Column("exceptions_json", sa.JSON(), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_business_calendars_environment_id", "business_calendars", ["environment_id"])
    op.create_table("sla_instances", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("case_id", sa.Uuid(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False), sa.Column("policy_id", sa.Uuid(), sa.ForeignKey("sla_policies.id"), nullable=False), sa.Column("started_at", sa.DateTime(timezone=True), nullable=False), sa.Column("response_due_at", sa.DateTime(timezone=True)), sa.Column("resolution_due_at", sa.DateTime(timezone=True)), sa.Column("response_warning_at", sa.DateTime(timezone=True)), sa.Column("resolution_warning_at", sa.DateTime(timezone=True)), sa.Column("first_response_at", sa.DateTime(timezone=True)), sa.Column("resolved_at", sa.DateTime(timezone=True)), sa.Column("response_status", sa.String(30), nullable=False), sa.Column("resolution_status", sa.String(30), nullable=False), sa.Column("accumulated_pause_seconds", sa.Integer(), nullable=False), sa.Column("active_pause_started_at", sa.DateTime(timezone=True)), sa.Column("superseded_at", sa.DateTime(timezone=True)), sa.Column("last_calculated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_sla_instances_case_id", "sla_instances", ["case_id"])
    op.create_index("ix_sla_instances_policy_id", "sla_instances", ["policy_id"])
    op.create_table("sla_pauses", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("instance_id", sa.Uuid(), sa.ForeignKey("sla_instances.id", ondelete="CASCADE"), nullable=False), sa.Column("started_at", sa.DateTime(timezone=True), nullable=False), sa.Column("ended_at", sa.DateTime(timezone=True)), sa.Column("reason", sa.String(120), nullable=False), sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id")), sa.Column("duration_seconds", sa.Integer()))
    op.create_index("ix_sla_pauses_instance_id", "sla_pauses", ["instance_id"])
    op.create_table("sla_events", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("instance_id", sa.Uuid(), sa.ForeignKey("sla_instances.id", ondelete="CASCADE"), nullable=False), sa.Column("case_id", sa.Uuid(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False), sa.Column("target", sa.String(30), nullable=False), sa.Column("event_type", sa.String(40), nullable=False), sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False), sa.Column("details_json", sa.JSON(), nullable=False))
    op.create_index("ix_sla_events_instance_id", "sla_events", ["instance_id"])
    op.create_index("ix_sla_events_case_id", "sla_events", ["case_id"])


def downgrade() -> None:
    for table in ("sla_events", "sla_pauses", "sla_instances", "business_calendars"):
        op.drop_table(table)
    with op.batch_alter_table("sla_policies") as batch:
        for column in ("recalculate_on_change", "precedence", "notification_json", "pause_rules_json", "conditions_json", "priority_option_id"):
            batch.drop_column(column)
