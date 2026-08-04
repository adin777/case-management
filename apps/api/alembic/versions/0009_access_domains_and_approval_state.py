"""Add business access domains and complete approval state.

Revision ID: 0009
Revises: 0008
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "permission_domains",
        sa.Column("code", sa.String(80), primary_key=True),
        sa.Column("name_he", sa.String(200), nullable=False),
        sa.Column("description_he", sa.Text(), nullable=False),
        sa.Column("scope", sa.String(30), nullable=False, server_default="environment"),
        sa.Column("view_permissions", sa.Text(), nullable=False, server_default=""),
        sa.Column("edit_permissions", sa.Text(), nullable=False, server_default=""),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "access_level_assignments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("domain_code", sa.String(80), sa.ForeignKey("permission_domains.code"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("group_id", sa.Uuid(), sa.ForeignKey("groups.id", ondelete="CASCADE")),
        sa.Column("environment_id", sa.Uuid(), sa.ForeignKey("environments.id", ondelete="CASCADE")),
        sa.Column("access_level", sa.String(10), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("access_level in ('none','view','edit')", name="ck_access_level_value"),
        sa.CheckConstraint("(user_id is null) != (group_id is null)", name="ck_access_level_one_subject"),
        sa.UniqueConstraint("domain_code", "user_id", "environment_id"),
        sa.UniqueConstraint("domain_code", "group_id", "environment_id"),
    )
    with op.batch_alter_table("cases") as batch:
        batch.add_column(sa.Column("approval_status", sa.String(30), nullable=False, server_default="not_started"))
        batch.add_column(sa.Column("is_approved", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("approved_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("approved_by_summary", sa.Text()))
    with op.batch_alter_table("audit_events") as batch:
        batch.add_column(sa.Column("actor_name_snapshot", sa.String(200)))
        batch.add_column(sa.Column("actor_email_snapshot", sa.String(320)))
    with op.batch_alter_table("approval_step_definitions") as batch:
        batch.add_column(sa.Column("approver_environment_role", sa.String(80)))
        batch.add_column(sa.Column("approver_user_field_id", sa.Uuid()))
        batch.add_column(sa.Column("approver_case_field_id", sa.Uuid()))
        batch.add_column(sa.Column("approval_mode", sa.String(30), nullable=False, server_default="any"))
        batch.add_column(sa.Column("description", sa.Text()))
        batch.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    with op.batch_alter_table("approval_step_definitions") as batch:
        for name in ("is_active", "description", "approval_mode", "approver_case_field_id", "approver_user_field_id", "approver_environment_role"):
            batch.drop_column(name)
    with op.batch_alter_table("audit_events") as batch:
        batch.drop_column("actor_email_snapshot")
        batch.drop_column("actor_name_snapshot")
    with op.batch_alter_table("cases") as batch:
        batch.drop_column("approved_by_summary")
        batch.drop_column("approved_at")
        batch.drop_column("is_approved")
        batch.drop_column("approval_status")
    op.drop_table("access_level_assignments")
    op.drop_table("permission_domains")
