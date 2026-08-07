"""Ensure the audit environment foreign key exists after SQLite batch upgrades.

Revision ID: 0008
Revises: 0007
"""

from collections.abc import Sequence

from sqlalchemy import inspect

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    foreign_keys = inspect(op.get_bind()).get_foreign_keys("audit_events")
    has_environment_fk = any(fk["constrained_columns"] == ["environment_id"] for fk in foreign_keys)
    if not has_environment_fk:
        with op.batch_alter_table("audit_events") as batch:
            batch.create_foreign_key(
                "fk_audit_events_environment_id",
                "environments",
                ["environment_id"],
                ["id"],
            )


def downgrade() -> None:
    foreign_keys = inspect(op.get_bind()).get_foreign_keys("audit_events")
    if any(fk.get("name") == "fk_audit_events_environment_id" for fk in foreign_keys):
        with op.batch_alter_table("audit_events") as batch:
            batch.drop_constraint("fk_audit_events_environment_id", type_="foreignkey")
