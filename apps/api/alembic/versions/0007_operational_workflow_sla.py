"""Add configurable workflow, SLA, attachments, notifications, and audit context.

Revision ID: 0007
Revises: 0006
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "workflow_definitions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("system_number", sa.String(40), nullable=False, unique=True),
        sa.Column("environment_id", sa.Uuid(), sa.ForeignKey("environments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name_he", sa.String(200), nullable=False),
        sa.Column("name_en", sa.String(200)),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_workflow_definitions_system_number", "workflow_definitions", ["system_number"], unique=True)
    op.create_index("ix_workflow_definitions_environment_id", "workflow_definitions", ["environment_id"])
    op.create_table(
        "workflow_statuses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workflow_id", sa.Uuid(), sa.ForeignKey("workflow_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(80), nullable=False), sa.Column("label_he", sa.String(200), nullable=False),
        sa.Column("label_en", sa.String(200)), sa.Column("description", sa.Text()),
        sa.Column("color", sa.String(20), nullable=False, server_default="#64748b"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_initial", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_final", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_closed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("workflow_id", "code"),
    )
    op.create_index("ix_workflow_statuses_workflow_id", "workflow_statuses", ["workflow_id"])
    op.create_table(
        "workflow_transitions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workflow_id", sa.Uuid(), sa.ForeignKey("workflow_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_status_id", sa.Uuid(), sa.ForeignKey("workflow_statuses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_status_id", sa.Uuid(), sa.ForeignKey("workflow_statuses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label_he", sa.String(200), nullable=False), sa.Column("description", sa.Text()),
        sa.Column("required_permission_code", sa.String(120)),
        sa.Column("requires_comment", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("requires_resolution", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("workflow_id", "from_status_id", "to_status_id"),
    )
    op.create_index("ix_workflow_transitions_workflow_id", "workflow_transitions", ["workflow_id"])
    op.create_table(
        "sla_policies",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("system_number", sa.String(40), nullable=False, unique=True),
        sa.Column("environment_id", sa.Uuid(), sa.ForeignKey("environments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_type_id", sa.Uuid(), sa.ForeignKey("request_types.id")),
        sa.Column("priority_id", sa.Uuid(), sa.ForeignKey("priority_definitions.id")),
        sa.Column("name_he", sa.String(200), nullable=False), sa.Column("description", sa.Text()),
        sa.Column("response_minutes", sa.Integer(), nullable=False), sa.Column("resolution_minutes", sa.Integer(), nullable=False),
        sa.Column("warning_threshold_percent", sa.Integer(), nullable=False, server_default="80"),
        sa.Column("business_calendar_id", sa.Uuid()), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(),
    )
    op.create_index("ix_sla_policies_system_number", "sla_policies", ["system_number"], unique=True)
    op.create_index("ix_sla_policies_environment_id", "sla_policies", ["environment_id"])
    with op.batch_alter_table("cases") as batch:
        batch.add_column(sa.Column("workflow_status_id", sa.Uuid()))
        batch.add_column(sa.Column("sla_policy_id", sa.Uuid()))
        batch.add_column(sa.Column("response_due_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("resolution_due_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("first_response_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("resolved_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("sla_response_status", sa.String(30), nullable=False, server_default="not_started"))
        batch.add_column(sa.Column("sla_resolution_status", sa.String(30), nullable=False, server_default="not_started"))
    op.create_table(
        "case_status_history", sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("case_id", sa.Uuid(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_status_id", sa.Uuid(), sa.ForeignKey("workflow_statuses.id")),
        sa.Column("to_status_id", sa.Uuid(), sa.ForeignKey("workflow_statuses.id"), nullable=False),
        sa.Column("transition_id", sa.Uuid(), sa.ForeignKey("workflow_transitions.id")),
        sa.Column("changed_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False), sa.Column("comment", sa.Text()),
        sa.Column("automation_summary", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_case_status_history_case_id", "case_status_history", ["case_id"])
    op.create_table(
        "attachments", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("system_number", sa.String(40), nullable=False, unique=True),
        sa.Column("case_id", sa.Uuid(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("comment_id", sa.Uuid(), sa.ForeignKey("comments.id")), sa.Column("original_file_name", sa.String(255), nullable=False),
        sa.Column("stored_file_name", sa.String(255), nullable=False, unique=True), sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False), sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False), sa.Column("uploaded_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("deleted_by", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_attachments_system_number", "attachments", ["system_number"], unique=True)
    op.create_index("ix_attachments_case_id", "attachments", ["case_id"])
    op.create_table(
        "notifications", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("notification_type", sa.String(80), nullable=False), sa.Column("title_he", sa.String(250), nullable=False),
        sa.Column("body_he", sa.Text(), nullable=False), sa.Column("entity_type", sa.String(80), nullable=False), sa.Column("entity_id", sa.String(100), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_user_unread", "notifications", ["user_id", "is_read"])
    op.create_table(
        "notification_outbox", sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("notification_id", sa.Uuid(), sa.ForeignKey("notifications.id", ondelete="CASCADE")),
        sa.Column("channel", sa.String(30), nullable=False), sa.Column("payload_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"), sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("processed_at", sa.DateTime(timezone=True)),
    )
    with op.batch_alter_table("audit_events") as batch:
        batch.add_column(
            sa.Column(
                "environment_id",
                sa.Uuid(),
                sa.ForeignKey("environments.id", name="fk_audit_events_environment_id"),
            )
        )
        batch.add_column(sa.Column("ip_address", sa.String(64)))
        batch.add_column(sa.Column("user_agent", sa.String(500)))


def downgrade() -> None:
    with op.batch_alter_table("audit_events") as batch:
        batch.drop_column("user_agent"); batch.drop_column("ip_address"); batch.drop_column("environment_id")
    op.drop_table("notification_outbox"); op.drop_index("ix_notifications_user_unread", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications"); op.drop_table("notifications")
    op.drop_index("ix_attachments_case_id", table_name="attachments"); op.drop_index("ix_attachments_system_number", table_name="attachments"); op.drop_table("attachments")
    op.drop_index("ix_case_status_history_case_id", table_name="case_status_history"); op.drop_table("case_status_history")
    with op.batch_alter_table("cases") as batch:
        for name in ("sla_resolution_status", "sla_response_status", "resolved_at", "first_response_at", "resolution_due_at", "response_due_at", "sla_policy_id", "workflow_status_id"):
            batch.drop_column(name)
    op.drop_index("ix_sla_policies_environment_id", table_name="sla_policies"); op.drop_index("ix_sla_policies_system_number", table_name="sla_policies"); op.drop_table("sla_policies")
    op.drop_index("ix_workflow_transitions_workflow_id", table_name="workflow_transitions"); op.drop_table("workflow_transitions")
    op.drop_index("ix_workflow_statuses_workflow_id", table_name="workflow_statuses"); op.drop_table("workflow_statuses")
    op.drop_index("ix_workflow_definitions_environment_id", table_name="workflow_definitions"); op.drop_index("ix_workflow_definitions_system_number", table_name="workflow_definitions"); op.drop_table("workflow_definitions")
