"""Make Global Field options the canonical semantic value catalog.

Revision ID: 0027
Revises: 0026
"""
import json
import uuid
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None

BINDINGS = {
    "case.status": ("workflow_status_id", "global_status_definitions"),
    "case.priority": ("priority_id", "global_priority_definitions"),
    "case.sub_priority": ("sub_priority_id", "global_sub_priority_definitions"),
}


def _scalar(value: object) -> object:
    if isinstance(value, list) and len(value) == 1:
        return value[0]
    return value


def _canonical_uuid(value: object) -> str:
    return str(uuid.UUID(str(value)))


def _db_uuid(value: object, connection: sa.Connection) -> str:
    parsed = uuid.UUID(str(value))
    return parsed.hex if connection.dialect.name == "sqlite" else str(parsed)


def upgrade() -> None:
    op.create_table(
        "global_case_field_options",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("global_field_id", sa.Uuid(), sa.ForeignKey(
            "global_case_field_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label_he", sa.String(200), nullable=False),
        sa.Column("label_en", sa.String(200), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_global_case_field_options_field", "global_case_field_options", ["global_field_id"])
    connection = op.get_bind()
    now = datetime.now(UTC)
    fields = connection.execute(sa.text(
        "SELECT id, field_type, semantic_binding, configuration_json "
        "FROM global_case_field_definitions"
    )).mappings().all()
    options_by_field: dict[str, list[dict]] = {}
    for field in fields:
        configuration = json.loads(field["configuration_json"] or "{}")
        options = configuration.pop("options", [])
        options_by_field[str(field["id"])] = options
        for option in options:
            connection.execute(sa.text(
                "INSERT INTO global_case_field_options "
                "(id,global_field_id,label_he,label_en,is_active,sort_order,metadata_json,created_at,updated_at) "
                "VALUES (:id,:field,:he,:en,:active,:sort,:metadata,:created,:updated)"
            ), {"id": _db_uuid(option["id"], connection), "field": field["id"], "he": option.get("label_he", ""),
                "en": option.get("label_en", ""), "active": option.get("is_active", True),
                "sort": option.get("sort_order", 0), "metadata": json.dumps(option.get("metadata", {})),
                "created": now, "updated": now})
        connection.execute(sa.text(
            "UPDATE global_case_field_definitions SET configuration_json=:configuration WHERE id=:id"
        ), {"configuration": json.dumps(configuration), "id": field["id"]})

    for field in fields:
        binding = field["semantic_binding"]
        if binding not in BINDINGS:
            continue
        column, legacy_table = BINDINGS[binding]
        option_rows = connection.execute(sa.text(
            "SELECT id,label_he FROM global_case_field_options WHERE global_field_id=:field"
        ), {"field": field["id"]}).mappings().all()
        option_ids = {_canonical_uuid(row["id"]) for row in option_rows}
        by_label = {str(row["label_he"]).strip().casefold(): _canonical_uuid(row["id"]) for row in option_rows}
        legacy_rows = connection.execute(sa.text(f"SELECT * FROM {legacy_table}")).mappings().all()
        for legacy in legacy_rows:
            option_id = by_label.get(str(legacy["label_he"]).strip().casefold())
            if not option_id:
                continue
            metadata = {"legacy_id":str(legacy["id"]), "code":legacy.get("code", "")}
            for key in ("semantic_category", "is_initial", "is_final", "color"):
                if key in legacy:
                    metadata[key] = legacy[key]
            connection.execute(sa.text(
                "UPDATE global_case_field_options SET metadata_json=:metadata WHERE id=:id"
            ), {"metadata":json.dumps(metadata), "id":_db_uuid(option_id, connection)})
            if binding == "case.status":
                connection.execute(sa.text(
                    "UPDATE workflow_transitions SET from_status_id=:option WHERE from_status_id=:legacy"
                ), {"option":_db_uuid(option_id, connection), "legacy":legacy["id"]})
                connection.execute(sa.text(
                    "UPDATE workflow_transitions SET to_status_id=:option WHERE to_status_id=:legacy"
                ), {"option":_db_uuid(option_id, connection), "legacy":legacy["id"]})
        cases = connection.execute(sa.text(
            f"SELECT c.id,c.{column} AS legacy,v.value_json FROM cases c "
            "LEFT JOIN global_case_field_values v ON v.case_id=c.id AND v.global_field_id=:field"
        ), {"field": field["id"]}).mappings().all()
        for case in cases:
            raw = json.loads(case["value_json"]) if case["value_json"] is not None else None
            value = _scalar(raw)
            canonical = _canonical_uuid(value) if value else None
            if canonical and canonical not in option_ids:
                legacy = connection.execute(sa.text(
                    f"SELECT label_he FROM {legacy_table} WHERE id=:id"
                ), {"id": _db_uuid(canonical, connection)}).mappings().first()
                canonical = by_label.get(str(legacy["label_he"]).strip().casefold()) if legacy else None
            if not canonical and case["legacy"]:
                legacy = connection.execute(sa.text(
                    f"SELECT label_he FROM {legacy_table} WHERE id=:id"
                ), {"id": case["legacy"]}).mappings().first()
                canonical = by_label.get(str(legacy["label_he"]).strip().casefold()) if legacy else None
            if canonical:
                connection.execute(sa.text(
                    "INSERT INTO global_case_field_values(case_id,global_field_id,value_json) "
                    "VALUES (:case,:field,:value) ON CONFLICT(case_id,global_field_id) "
                    "DO UPDATE SET value_json=:value"
                ), {"case": case["id"], "field": field["id"], "value": json.dumps(canonical)})
                connection.execute(sa.text(f"UPDATE cases SET {column}=:value WHERE id=:case"),
                    {"value": _db_uuid(canonical, connection), "case": case["id"]})
            elif value or case["legacy"]:
                connection.execute(sa.text(
                    "INSERT INTO case_semantic_sync_conflicts "
                    "(id,case_id,semantic_binding,global_value_json,optimized_value_id,reason,created_at,updated_at) "
                    "VALUES (:id,:case,:binding,:global,:legacy,'unmapped_legacy_value',:created,:updated)"
                ), {"id": _db_uuid(uuid.uuid4(), connection), "case": case["id"], "binding": binding,
                    "global": json.dumps(raw), "legacy": case["legacy"], "created": now, "updated": now})
    with op.batch_alter_table("cases") as batch:
        batch.drop_constraint("fk_cases_global_priority_id", type_="foreignkey")
        batch.drop_constraint("fk_cases_global_sub_priority_id", type_="foreignkey")


def downgrade() -> None:
    with op.batch_alter_table("cases") as batch:
        batch.create_foreign_key("fk_cases_global_priority_id", "global_priority_definitions", ["priority_id"], ["id"])
        batch.create_foreign_key("fk_cases_global_sub_priority_id", "global_sub_priority_definitions", ["sub_priority_id"], ["id"])
    op.drop_index("ix_global_case_field_options_field", table_name="global_case_field_options")
    op.drop_table("global_case_field_options")
