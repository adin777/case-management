"""Migrate automations to stable Global Field IDs and retire legacy catalogs.

Revision ID: 0028
Revises: 0027
"""
import json
import uuid
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None

BINDINGS = {
    "status": "case.status",
    "priority": "case.priority",
    "sub_priority": "case.sub_priority",
    "assignee": "case.assignee",
}


def _db_uuid(value: object, connection: sa.Connection) -> str:
    parsed = uuid.UUID(str(value))
    return parsed.hex if connection.dialect.name == "sqlite" else str(parsed)


def upgrade() -> None:
    op.create_table(
        "automation_migration_conflicts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("rule_id", sa.Uuid(), sa.ForeignKey("automation_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reason", sa.String(100), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    connection = op.get_bind()
    fields = connection.execute(sa.text(
        "SELECT id, semantic_binding FROM global_case_field_definitions "
        "WHERE semantic_binding IS NOT NULL AND is_active=1"
    )).mappings().all()
    by_binding = {row["semantic_binding"]: row["id"] for row in fields}
    options = connection.execute(sa.text(
        "SELECT id, metadata_json FROM global_case_field_options"
    )).mappings().all()
    legacy_options: dict[str, str] = {}
    for option in options:
        metadata = json.loads(option["metadata_json"] or "{}")
        if metadata.get("legacy_id"):
            legacy_options[str(metadata["legacy_id"]).replace("-", "")] = str(uuid.UUID(str(option["id"])))

    for rule in connection.execute(sa.text(
        "SELECT id, conditions_json, actions_json FROM automation_rules"
    )).mappings().all():
        conditions = json.loads(rule["conditions_json"] or "{}")
        actions = json.loads(rule["actions_json"] or "[]")
        conflict = False
        for condition in conditions.get("conditions", []):
            old = condition.get("field")
            binding = BINDINGS.get(old)
            if binding:
                field_id = by_binding.get(binding)
                if not field_id:
                    conflict = True
                    continue
                condition["field"] = str(uuid.UUID(str(field_id)))
            value = condition.get("value")
            if value and str(value).replace("-", "") in legacy_options:
                condition["value"] = legacy_options[str(value).replace("-", "")]
        for action in actions:
            old = action.pop("field_code", None)
            binding = BINDINGS.get(old)
            if binding:
                field_id = by_binding.get(binding)
                if not field_id:
                    conflict = True
                else:
                    action["field_id"] = str(uuid.UUID(str(field_id)))
            value = action.get("value_id", action.get("value"))
            if value and str(value).replace("-", "") in legacy_options:
                if "value_id" in action:
                    action["value_id"] = legacy_options[str(value).replace("-", "")]
                else:
                    action["value"] = legacy_options[str(value).replace("-", "")]
        connection.execute(sa.text(
            "UPDATE automation_rules SET conditions_json=:conditions, actions_json=:actions, "
            "is_active=:active WHERE id=:id"
        ), {"conditions": json.dumps(conditions), "actions": json.dumps(actions),
            "active": not conflict, "id": rule["id"]})
        if conflict:
            connection.execute(sa.text(
                "INSERT INTO automation_migration_conflicts(id,rule_id,reason,payload_json,created_at) "
                "VALUES (:id,:rule,'unmapped_field',:payload,:created)"
            ), {"id": _db_uuid(uuid.uuid4(), connection), "rule": rule["id"],
                "payload": json.dumps({"conditions": conditions, "actions": actions}),
                "created": datetime.now(UTC)})
    for table in ("global_status_definitions", "global_priority_definitions",
                  "global_sub_priority_definitions"):
        connection.execute(sa.text(f"UPDATE {table} SET is_active=0"))


def downgrade() -> None:
    op.drop_table("automation_migration_conflicts")
