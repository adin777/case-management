"""Normalize legacy system-number index names.

Revision ID: 0006
Revises: 0005
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import inspect

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "automation_rules", "groups", "priority_definitions", "request_types",
    "sub_priority_definitions", "user_field_definitions",
)


def upgrade() -> None:
    connection = op.get_bind()
    for table in TABLES:
        names = {item["name"] for item in inspect(connection).get_indexes(table)}
        legacy = f"ux_{table}_system_number"
        canonical = f"ix_{table}_system_number"
        if legacy in names and canonical not in names:
            op.drop_index(legacy, table_name=table)
            op.create_index(canonical, table, ["system_number"], unique=True)


def downgrade() -> None:
    connection = op.get_bind()
    for table in TABLES:
        names = {item["name"] for item in inspect(connection).get_indexes(table)}
        legacy = f"ux_{table}_system_number"
        canonical = f"ix_{table}_system_number"
        if canonical in names and legacy not in names:
            op.drop_index(canonical, table_name=table)
            op.create_index(legacy, table, ["system_number"], unique=True)
