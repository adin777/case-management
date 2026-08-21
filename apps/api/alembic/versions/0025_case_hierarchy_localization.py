"""Add case hierarchy and generic localization.

Revision ID: 0025
Revises: 0024
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("languages",
        sa.Column("code", sa.String(12), primary_key=True), sa.Column("name", sa.String(100), nullable=False),
        sa.Column("native_name", sa.String(100), nullable=False), sa.Column("direction", sa.String(3), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False), sa.Column("is_default", sa.Boolean(), nullable=False))
    op.bulk_insert(sa.table("languages", sa.column("code", sa.String), sa.column("name", sa.String),
        sa.column("native_name", sa.String), sa.column("direction", sa.String), sa.column("is_active", sa.Boolean),
        sa.column("is_default", sa.Boolean)), [
            {"code":"he","name":"Hebrew","native_name":"עברית","direction":"rtl","is_active":True,"is_default":True},
            {"code":"en","name":"English","native_name":"English","direction":"ltr","is_active":True,"is_default":False},
        ])
    op.create_table("entity_translations", sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("entity_type", sa.String(80), nullable=False), sa.Column("entity_id", sa.String(80), nullable=False),
        sa.Column("field_name", sa.String(80), nullable=False), sa.Column("language_code", sa.String(12), sa.ForeignKey("languages.code"), nullable=False),
        sa.Column("value", sa.Text(), nullable=False), sa.UniqueConstraint("entity_type","entity_id","field_name","language_code"))
    op.create_index("ix_entity_translations_entity_type", "entity_translations", ["entity_type"])
    op.create_index("ix_entity_translations_entity_id", "entity_translations", ["entity_id"])
    op.create_table("case_relations", sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("parent_case_id", sa.Uuid(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("child_case_id", sa.Uuid(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("relation_type", sa.String(30), nullable=False), sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("parent_case_id","child_case_id","relation_type"))
    op.create_index("ix_case_relations_parent_case_id", "case_relations", ["parent_case_id"])
    op.create_index("ix_case_relations_child_case_id", "case_relations", ["child_case_id"])
    op.create_table("case_status_change_previews", sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("parent_case_id", sa.Uuid(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_status_id", sa.Uuid(), sa.ForeignKey("global_status_definitions.id"), nullable=False),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("include_descendants", sa.Boolean(), nullable=False), sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_case_status_change_previews_parent_case_id", "case_status_change_previews", ["parent_case_id"])
    op.create_index("ix_case_status_change_previews_actor_id", "case_status_change_previews", ["actor_id"])


def downgrade() -> None:
    op.drop_table("case_status_change_previews")
    op.drop_table("case_relations")
    op.drop_table("entity_translations")
    op.drop_table("languages")
