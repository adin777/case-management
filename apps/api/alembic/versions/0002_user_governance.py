"""Add user governance, configurable priorities and collaboration metadata."""

import sqlalchemy as sa
from sqlalchemy.schema import SchemaItem

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

uuid_type = sa.Uuid()
timestamp = sa.DateTime(timezone=True)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    def add_if_missing(table: str, column: sa.Column) -> None:
        if column.name not in {item["name"] for item in inspector.get_columns(table)}:
            op.add_column(table, column)

    existing_tables = set(inspector.get_table_names())

    def create_table(name: str, *columns: SchemaItem) -> None:
        if name not in existing_tables:
            op.create_table(name, *columns)

    add_if_missing("users", sa.Column("last_login_at", timestamp))
    add_if_missing("groups", sa.Column("created_at", timestamp, server_default=sa.func.now()))
    add_if_missing("groups", sa.Column("updated_at", timestamp, server_default=sa.func.now()))
    add_if_missing("group_members", sa.Column("added_at", timestamp, server_default=sa.func.now()))
    # SQLite cannot add a foreign-key constraint to an existing table without rebuilding it.
    # The application validates this development-only audit reference and keeps all existing rows intact.
    add_if_missing("group_members", sa.Column("added_by", uuid_type))
    add_if_missing("roles", sa.Column("description", sa.Text()))
    add_if_missing("roles", sa.Column("scope", sa.String(20), server_default="environment"))
    with op.batch_alter_table("groups") as batch:
        batch.alter_column("created_at", existing_type=timestamp, nullable=False)
        batch.alter_column("updated_at", existing_type=timestamp, nullable=False)
    group_member_foreign_keys = {fk.get("name") for fk in inspector.get_foreign_keys("group_members")}
    with op.batch_alter_table("group_members") as batch:
        batch.alter_column("added_at", existing_type=timestamp, nullable=False)
        if "fk_group_members_added_by" not in group_member_foreign_keys:
            batch.create_foreign_key("fk_group_members_added_by", "users", ["added_by"], ["id"])
    with op.batch_alter_table("roles") as batch:
        batch.alter_column("scope", existing_type=sa.String(20), nullable=False)

    create_table(
        "permissions",
        sa.Column("code", sa.String(120), primary_key=True),
        sa.Column("description", sa.Text()),
    )
    create_table(
        "role_permissions",
        sa.Column("role_id", uuid_type, sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column(
            "permission_code",
            sa.String(120),
            sa.ForeignKey("permissions.code", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    create_table(
        "group_environment_roles",
        sa.Column(
            "environment_id",
            uuid_type,
            sa.ForeignKey("environments.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("group_id", uuid_type, sa.ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", uuid_type, sa.ForeignKey("roles.id"), primary_key=True),
    )
    create_table(
        "user_field_definitions",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("key", sa.String(80), nullable=False, unique=True),
        sa.Column("label_he", sa.String(200), nullable=False),
        sa.Column("label_en", sa.String(200), nullable=False),
        sa.Column("field_type", sa.String(40), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("options_json", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("default_value_json", sa.JSON()),
        sa.Column("validation_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", timestamp, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", timestamp, server_default=sa.func.now(), nullable=False),
    )
    create_table(
        "user_field_values",
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column(
            "field_id",
            uuid_type,
            sa.ForeignKey("user_field_definitions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("value_json", sa.JSON()),
    )
    create_table(
        "environment_user_fields",
        sa.Column(
            "environment_id",
            uuid_type,
            sa.ForeignKey("environments.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_field_definition_id",
            uuid_type,
            sa.ForeignKey("user_field_definitions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_editable_by_user", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_editable_by_environment_admin", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    create_table(
        "automation_rules",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("environment_id", uuid_type, sa.ForeignKey("environments.id")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("trigger_type", sa.String(60), nullable=False),
        sa.Column("conditions_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("actions_json", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", timestamp, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", timestamp, server_default=sa.func.now(), nullable=False),
    )
    create_table(
        "priority_definitions",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "environment_id", uuid_type, sa.ForeignKey("environments.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("label_he", sa.String(100), nullable=False),
        sa.Column("color", sa.String(20), nullable=False, server_default="#64748b"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("environment_id", "code"),
    )
    create_table(
        "sub_priority_definitions",
        sa.Column(
            "id", uuid_type, primary_key=True
        ),
        sa.Column(
            "priority_id", uuid_type, sa.ForeignKey("priority_definitions.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("label_he", sa.String(100), nullable=False),
        sa.Column("color", sa.String(20), nullable=False, server_default="#64748b"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("priority_id", "code"),
    )
    case_columns = {item["name"] for item in inspector.get_columns("cases")}
    with op.batch_alter_table("cases") as batch:
        if "priority_id" not in case_columns:
            batch.add_column(sa.Column("priority_id", uuid_type))
            batch.create_foreign_key("fk_cases_priority_id", "priority_definitions", ["priority_id"], ["id"])
        if "sub_priority_id" not in case_columns:
            batch.add_column(sa.Column("sub_priority_id", uuid_type))
            batch.create_foreign_key(
                "fk_cases_sub_priority_id", "sub_priority_definitions", ["sub_priority_id"], ["id"]
            )


def downgrade() -> None:
    with op.batch_alter_table("cases") as batch:
        batch.drop_column("sub_priority_id")
        batch.drop_column("priority_id")
    for table in [
        "sub_priority_definitions",
        "priority_definitions",
        "automation_rules",
        "environment_user_fields",
        "user_field_values",
        "user_field_definitions",
        "group_environment_roles",
        "role_permissions",
        "permissions",
    ]:
        op.drop_table(table)
    op.drop_column("roles", "scope")
    op.drop_column("roles", "description")
    op.drop_column("group_members", "added_by")
    op.drop_column("group_members", "added_at")
    op.drop_column("groups", "updated_at")
    op.drop_column("groups", "created_at")
    op.drop_column("users", "last_login_at")
