"""Add configurable platform, direct permissions, reports and approvals."""

import uuid

import sqlalchemy as sa
from sqlalchemy.schema import SchemaItem

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

uuid_type = sa.Uuid()
timestamp = sa.DateTime(timezone=True)


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    def create_table(name: str, *columns: SchemaItem) -> None:
        if name not in inspector.get_table_names():
            op.create_table(name, *columns)

    for table, columns in {
        "groups": [sa.Column("system_number", sa.String(40))],
        "request_types": [
            sa.Column("system_number", sa.String(40)),
            sa.Column("default_priority_id", uuid_type),
            sa.Column("default_sub_priority_id", uuid_type),
            sa.Column("default_assignee_user_id", uuid_type),
            sa.Column("default_assignee_group_id", uuid_type),
            sa.Column("workflow_definition_id", uuid_type),
        ],
        "user_field_definitions": [sa.Column("system_number", sa.String(40))],
        "automation_rules": [sa.Column("system_number", sa.String(40))],
        "priority_definitions": [
            sa.Column("system_number", sa.String(40)),
            sa.Column("label_en", sa.String(100), server_default=""),
            sa.Column("description", sa.Text()),
        ],
        "sub_priority_definitions": [
            sa.Column("system_number", sa.String(40)),
            sa.Column("label_en", sa.String(100), server_default=""),
            sa.Column("description", sa.Text()),
        ],
        "permissions": [
            sa.Column("name_he", sa.String(160)),
            sa.Column("description_he", sa.Text()),
            sa.Column("category", sa.String(100)),
            sa.Column("scope", sa.String(30)),
        ],
    }.items():
        existing_columns = {item["name"] for item in inspector.get_columns(table)}
        for column in columns:
            if column.name not in existing_columns:
                op.add_column(table, column)

    prefixes = {
        "groups": "UG",
        "request_types": "RT",
        "user_field_definitions": "UF",
        "automation_rules": "AR",
        "priority_definitions": "PR",
        "sub_priority_definitions": "SP",
    }
    for table, prefix in prefixes.items():
        rows = connection.execute(sa.text(f"select id from {table} order by rowid")).fetchall()
        for index, row in enumerate(rows, 1):
            connection.execute(
                sa.text(f"update {table} set system_number=:number where id=:id"),
                {"number": f"{prefix}-{index:06d}", "id": row[0]},
            )
        if f"ix_{table}_system_number" not in {item["name"] for item in inspector.get_indexes(table)}:
            op.create_index(f"ix_{table}_system_number", table, ["system_number"], unique=True)

    create_table(
        "numbering_series",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("environment_id", uuid_type, sa.ForeignKey("environments.id")),
        sa.Column("prefix", sa.String(20), nullable=False),
        sa.Column("next_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("padding", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", timestamp, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("entity_type", "environment_id"),
    )
    for entity, prefix in {
        "case": "CASE",
        "request_type": "RT",
        "case_field": "CF",
        "user_field": "UF",
        "user_group": "UG",
        "approval_flow": "AF",
        "approval_instance": "AI",
        "automation_rule": "AR",
        "priority": "PR",
        "sub_priority": "SP",
    }.items():
        exists = connection.execute(
            sa.text("select 1 from numbering_series where entity_type=:entity and environment_id is null"),
            {"entity": entity},
        ).fetchone()
        if not exists:
            connection.execute(
                sa.text(
                    "insert into numbering_series (id,entity_type,prefix,next_number,padding,is_active) values (:id,:entity,:prefix,1,6,1)"
                ),
                {"id": uuid.uuid4().hex, "entity": entity, "prefix": prefix},
            )

    create_table(
        "case_field_definitions",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("system_number", sa.String(40), nullable=False, unique=True),
        sa.Column(
            "environment_id", uuid_type, sa.ForeignKey("environments.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("request_type_id", uuid_type, sa.ForeignKey("request_types.id", ondelete="CASCADE")),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("label_he", sa.String(200), nullable=False),
        sa.Column("label_en", sa.String(200), nullable=False, server_default=""),
        sa.Column("description", sa.Text()),
        sa.Column("field_type", sa.String(40), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("options_json", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("default_value_json", sa.JSON()),
        sa.Column("validation_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", timestamp, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("environment_id", "request_type_id", "key"),
    )
    for name, owner, owner_fk in [
        ("user_permission_assignments", "user_id", "users.id"),
        ("group_permission_assignments", "group_id", "groups.id"),
    ]:
        create_table(
            name,
            sa.Column("id", uuid_type, primary_key=True),
            sa.Column(owner, uuid_type, sa.ForeignKey(owner_fk, ondelete="CASCADE"), nullable=False),
            sa.Column(
                "permission_code",
                sa.String(120),
                sa.ForeignKey("permissions.code", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("environment_id", uuid_type, sa.ForeignKey("environments.id", ondelete="CASCADE")),
            sa.Column("is_allowed", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_by", uuid_type, sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", timestamp, nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", timestamp, nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint(owner, "permission_code", "environment_id"),
        )

    create_table(
        "automation_execution_logs",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "rule_id", uuid_type, sa.ForeignKey("automation_rules.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("case_id", uuid_type, sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trigger_type", sa.String(60), nullable=False),
        sa.Column("matched", sa.Boolean(), nullable=False),
        sa.Column("actions_executed", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("error", sa.Text()),
        sa.Column("executed_at", timestamp, nullable=False, server_default=sa.func.now()),
    )
    create_table(
        "approval_flow_definitions",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("system_number", sa.String(40), nullable=False, unique=True),
        sa.Column(
            "environment_id", uuid_type, sa.ForeignKey("environments.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("request_type_id", uuid_type, sa.ForeignKey("request_types.id")),
        sa.Column("trigger_type", sa.String(60), nullable=False, server_default="case_created"),
        sa.Column("created_by", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", timestamp, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp, nullable=False, server_default=sa.func.now()),
    )
    create_table(
        "approval_step_definitions",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "approval_flow_id",
            uuid_type,
            sa.ForeignKey("approval_flow_definitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("approver_type", sa.String(40), nullable=False),
        sa.Column("approver_user_id", uuid_type, sa.ForeignKey("users.id")),
        sa.Column("approver_group_id", uuid_type, sa.ForeignKey("groups.id")),
        sa.Column("approver_field_key", sa.String(80)),
        sa.Column("required_approvals", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("allow_reject", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("allow_return", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("timeout_hours", sa.Integer()),
        sa.UniqueConstraint("approval_flow_id", "step_order"),
    )
    create_table(
        "approval_instances",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("system_number", sa.String(40), nullable=False, unique=True),
        sa.Column("case_id", uuid_type, sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "approval_flow_id", uuid_type, sa.ForeignKey("approval_flow_definitions.id"), nullable=False
        ),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("current_step_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("started_at", timestamp, nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", timestamp),
        sa.Column("cancelled_at", timestamp),
    )
    create_table(
        "approval_tasks",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "approval_instance_id",
            uuid_type,
            sa.ForeignKey("approval_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "step_definition_id", uuid_type, sa.ForeignKey("approval_step_definitions.id"), nullable=False
        ),
        sa.Column("approver_user_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("decision", sa.String(30)),
        sa.Column("comment", sa.Text()),
        sa.Column("decided_at", timestamp),
    )


def downgrade() -> None:
    for table in [
        "approval_tasks",
        "approval_instances",
        "approval_step_definitions",
        "approval_flow_definitions",
        "automation_execution_logs",
        "group_permission_assignments",
        "user_permission_assignments",
        "case_field_definitions",
        "numbering_series",
    ]:
        op.drop_table(table)
    for table in [
        "groups",
        "request_types",
        "user_field_definitions",
        "automation_rules",
        "priority_definitions",
        "sub_priority_definitions",
    ]:
        op.drop_index(f"ix_{table}_system_number", table_name=table)
    for table, columns in {
        "groups": ["system_number"],
        "request_types": [
            "workflow_definition_id",
            "default_assignee_group_id",
            "default_assignee_user_id",
            "default_sub_priority_id",
            "default_priority_id",
            "system_number",
        ],
        "user_field_definitions": ["system_number"],
        "automation_rules": ["system_number"],
        "priority_definitions": ["description", "label_en", "system_number"],
        "sub_priority_definitions": ["description", "label_en", "system_number"],
        "permissions": ["scope", "category", "description_he", "name_he"],
    }.items():
        with op.batch_alter_table(table) as batch:
            for column in columns:
                batch.drop_column(column)
