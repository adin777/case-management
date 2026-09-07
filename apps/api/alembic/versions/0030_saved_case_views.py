"""Add persistent agent workspace saved views.

Revision ID: 0030
Revises: 0029
"""
import sqlalchemy as sa

from alembic import op

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "saved_case_views",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("filters_json", sa.JSON(), nullable=False),
        sa.Column("sort", sa.String(80), nullable=False),
        sa.Column("visible_columns_json", sa.JSON(), nullable=False),
        sa.Column("page_size", sa.Integer(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "name"),
    )
    op.create_index("ix_saved_case_views_user_id", "saved_case_views", ["user_id"])
    op.create_table(
        "bulk_case_action_previews",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("target_value_json", sa.JSON(), nullable=False),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_bulk_case_action_previews_user_id", "bulk_case_action_previews", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_bulk_case_action_previews_user_id", table_name="bulk_case_action_previews")
    op.drop_table("bulk_case_action_previews")
    op.drop_index("ix_saved_case_views_user_id", table_name="saved_case_views")
    op.drop_table("saved_case_views")
