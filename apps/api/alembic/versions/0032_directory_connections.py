"""Add encrypted directory connections and immutable preview sessions.

Revision ID: 0032
Revises: 0031
"""
import sqlalchemy as sa

from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("auth_source",sa.String(30),nullable=False,server_default="local"))
        batch.create_index("ix_users_auth_source",["auth_source"])
    op.create_table("directory_connections",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("provider",sa.String(40),nullable=False,unique=True),sa.Column("configuration_json",sa.JSON(),nullable=False),sa.Column("encrypted_secret",sa.Text()),sa.Column("status",sa.String(40),nullable=False),sa.Column("last_tested_at",sa.DateTime(timezone=True)),sa.Column("last_successful_test_at",sa.DateTime(timezone=True)),sa.Column("last_sync_at",sa.DateTime(timezone=True)),sa.Column("last_sync_result",sa.String(40)),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_index("ix_directory_connections_provider","directory_connections",["provider"],unique=True)
    op.create_table("directory_preview_sessions",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("provider",sa.String(40),nullable=False),sa.Column("created_by",sa.Uuid(),sa.ForeignKey("users.id",ondelete="CASCADE"),nullable=False),sa.Column("snapshot_json",sa.JSON(),nullable=False),sa.Column("applied_at",sa.DateTime(timezone=True)),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_index("ix_directory_preview_sessions_provider","directory_preview_sessions",["provider"])


def downgrade() -> None:
    op.drop_table("directory_preview_sessions")
    op.drop_table("directory_connections")
    with op.batch_alter_table("users") as batch:
        batch.drop_index("ix_users_auth_source")
        batch.drop_column("auth_source")
