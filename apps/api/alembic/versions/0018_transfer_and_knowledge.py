"""Add safe case transfer history and environment knowledge base.

Revision ID: 0018
Revises: 0017
"""
import sqlalchemy as sa

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("case_transfer_histories",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("case_id", sa.Uuid(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_environment_id", sa.Uuid(), sa.ForeignKey("environments.id"), nullable=False), sa.Column("to_environment_id", sa.Uuid(), sa.ForeignKey("environments.id"), nullable=False),
        sa.Column("from_request_type_id", sa.Uuid(), sa.ForeignKey("request_types.id"), nullable=False), sa.Column("to_request_type_id", sa.Uuid(), sa.ForeignKey("request_types.id"), nullable=False),
        sa.Column("from_status_id", sa.Uuid()), sa.Column("to_status_id", sa.Uuid(), nullable=False), sa.Column("transferred_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("transferred_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("removed_participants", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("removed_assignee", sa.JSON()), sa.Column("removed_fields_snapshot", sa.JSON(), nullable=False, server_default="[]"), sa.Column("new_values", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("approval_effect", sa.JSON(), nullable=False, server_default="{}"), sa.Column("sla_effect", sa.JSON(), nullable=False, server_default="{}"), sa.Column("reason", sa.Text()))
    op.create_index("ix_case_transfer_histories_case_id", "case_transfer_histories", ["case_id"])
    op.create_table("knowledge_documents",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("environment_id", sa.Uuid(), sa.ForeignKey("environments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False), sa.Column("original_filename", sa.String(255), nullable=False), sa.Column("mime_type", sa.String(120), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False), sa.Column("storage_path", sa.String(500), nullable=False, unique=True), sa.Column("status", sa.String(30), nullable=False, server_default="uploaded"),
        sa.Column("uploaded_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False), sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("indexed_at", sa.DateTime(timezone=True)), sa.Column("version", sa.Integer(), nullable=False, server_default="1"), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("error_message", sa.Text()))
    op.create_index("ix_knowledge_documents_environment_id", "knowledge_documents", ["environment_id"])
    op.create_table("knowledge_chunks",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("document_id", sa.Uuid(), sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("environment_id", sa.Uuid(), sa.ForeignKey("environments.id", ondelete="CASCADE"), nullable=False), sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(200)), sa.Column("content", sa.Text(), nullable=False), sa.Column("embedding_json", sa.JSON(), nullable=False, server_default="[]"),
        sa.UniqueConstraint("document_id", "chunk_index"))
    op.create_index("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"])
    op.create_index("ix_knowledge_chunks_environment_id", "knowledge_chunks", ["environment_id"])


def downgrade() -> None:
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_documents")
    op.drop_table("case_transfer_histories")
