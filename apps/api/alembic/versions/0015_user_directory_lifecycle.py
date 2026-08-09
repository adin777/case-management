"""Add user lifecycle, directory sync, assignment rules and job-title approvals.

Revision ID: 0015
Revises: 0014
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        for name, length in (("first_name", 120), ("last_name", 120), ("user_principal_name", 320),
                             ("department", 200), ("job_title", 200), ("phone", 80),
                             ("mobile_phone", 80), ("employee_id", 120), ("computer_identifier", 200),
                             ("directory_object_id", 200), ("source", 30), ("status", 30)):
            batch.add_column(sa.Column(name, sa.String(length), nullable=True))
        batch.add_column(sa.Column("directory_enabled", sa.Boolean(), nullable=True))
        batch.add_column(sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("last_directory_sync_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE users SET source='manual', status=CASE WHEN is_active=1 THEN 'active' ELSE 'inactive' END")
    with op.batch_alter_table("users") as batch:
        batch.alter_column("source", existing_type=sa.String(30), nullable=False, server_default="manual")
        batch.alter_column("status", existing_type=sa.String(30), nullable=False, server_default="active")
        batch.create_index("ix_users_user_principal_name", ["user_principal_name"], unique=True)
        batch.create_index("ix_users_directory_object_id", ["directory_object_id"], unique=True)
        batch.create_index("ix_users_department", ["department"])
        batch.create_index("ix_users_job_title", ["job_title"])
        batch.create_index("ix_users_employee_id", ["employee_id"])
        batch.create_index("ix_users_source", ["source"])
        batch.create_index("ix_users_status", ["status"])
    with op.batch_alter_table("environment_memberships") as batch:
        batch.alter_column("role_id", existing_type=sa.Uuid(), nullable=True)
        batch.add_column(sa.Column("source", sa.String(30), nullable=False, server_default="manual"))
        batch.add_column(sa.Column("source_rule_id", sa.Uuid(), nullable=True))
    with op.batch_alter_table("approval_step_definitions") as batch:
        batch.add_column(sa.Column("approver_job_title", sa.String(200), nullable=True))
    op.create_table("directory_sync_runs", sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("provider", sa.String(40), nullable=False), sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True)), sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("updated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("disabled_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("unchanged_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("delta_reference", sa.Text()),
        sa.Column("initiated_by", sa.Uuid(), sa.ForeignKey("users.id")), sa.Column("error_summary", sa.Text()))
    op.create_table("environment_assignment_rules", sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("environment_id", sa.Uuid(), sa.ForeignKey("environments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False), sa.Column("conditions_json", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))


def downgrade() -> None:
    op.drop_table("environment_assignment_rules"); op.drop_table("directory_sync_runs")
    with op.batch_alter_table("approval_step_definitions") as batch: batch.drop_column("approver_job_title")
    with op.batch_alter_table("environment_memberships") as batch:
        batch.drop_column("source_rule_id"); batch.drop_column("source"); batch.alter_column("role_id", existing_type=sa.Uuid(), nullable=False)
    with op.batch_alter_table("users") as batch:
        for name in ("last_directory_sync_at", "archived_at", "status", "directory_enabled", "source", "directory_object_id", "computer_identifier", "employee_id", "mobile_phone", "phone", "job_title", "department", "user_principal_name", "last_name", "first_name"): batch.drop_column(name)
