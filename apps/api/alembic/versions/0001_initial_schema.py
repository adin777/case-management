"""Initial portable case-management schema."""

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

uuid_type = sa.Uuid()
timestamp = sa.DateTime(timezone=True)
form_status = sa.Enum("draft", "published", name="formstatus", native_enum=False)
case_status = sa.Enum(
    "draft",
    "submitted",
    "assigned",
    "in_progress",
    "waiting_for_requester",
    "resolved",
    "closed",
    "cancelled",
    name="casestatus",
    native_enum=False,
)
visibility = sa.Enum("public", "internal", name="visibility", native_enum=False)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("password_hash", sa.String(500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_system_admin", sa.Boolean(), nullable=False),
        sa.Column("created_at", timestamp, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", timestamp, server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "groups",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "roles",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "environments",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name_he", sa.String(200), nullable=False),
        sa.Column("name_en", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", timestamp, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", timestamp, server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "group_members",
        sa.Column("group_id", uuid_type, sa.ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "environment_memberships",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "environment_id", uuid_type, sa.ForeignKey("environments.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("group_id", uuid_type, sa.ForeignKey("groups.id", ondelete="CASCADE")),
        sa.Column("role_id", uuid_type, sa.ForeignKey("roles.id"), nullable=False),
        sa.UniqueConstraint("environment_id", "user_id", "role_id"),
    )
    op.create_table(
        "request_types",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "environment_id", uuid_type, sa.ForeignKey("environments.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name_he", sa.String(200), nullable=False),
        sa.Column("name_en", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("form_version_id", uuid_type),
        sa.Column("created_at", timestamp, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", timestamp, server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("environment_id", "code"),
    )
    op.create_table(
        "form_definitions",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "request_type_id",
            uuid_type,
            sa.ForeignKey("request_types.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", form_status, nullable=False),
        sa.Column("created_at", timestamp, server_default=sa.func.now(), nullable=False),
        sa.Column("published_at", timestamp),
        sa.UniqueConstraint("request_type_id", "version"),
    )
    op.create_table(
        "field_definitions",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "form_definition_id",
            uuid_type,
            sa.ForeignKey("form_definitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("label_he", sa.String(200), nullable=False),
        sa.Column("label_en", sa.String(200), nullable=False),
        sa.Column("field_type", sa.String(40), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("is_read_only", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("configuration_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("form_definition_id", "key"),
    )
    op.create_table(
        "cases",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("case_number", sa.String(40), nullable=False),
        sa.Column("environment_id", uuid_type, sa.ForeignKey("environments.id"), nullable=False),
        sa.Column("request_type_id", uuid_type, sa.ForeignKey("request_types.id"), nullable=False),
        sa.Column("form_definition_id", uuid_type, sa.ForeignKey("form_definitions.id"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", case_status, nullable=False),
        sa.Column("priority", sa.String(30), nullable=False),
        sa.Column("reporter_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("requester_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assignee_id", uuid_type, sa.ForeignKey("users.id")),
        sa.Column("assigned_group_id", uuid_type, sa.ForeignKey("groups.id")),
        sa.Column("created_at", timestamp, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", timestamp, server_default=sa.func.now(), nullable=False),
        sa.Column("closed_at", timestamp),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.UniqueConstraint("case_number"),
    )
    op.create_index("ix_cases_case_number", "cases", ["case_number"], unique=True)
    op.create_table(
        "case_field_values",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("case_id", uuid_type, sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_definition_id", uuid_type, sa.ForeignKey("field_definitions.id"), nullable=False),
        sa.Column("value_text", sa.Text()),
        sa.Column("value_number", sa.Numeric()),
        sa.Column("value_boolean", sa.Boolean()),
        sa.Column("value_date", sa.Date()),
        sa.Column("value_datetime", timestamp),
        sa.Column("value_user_id", uuid_type, sa.ForeignKey("users.id")),
        sa.Column("value_json", sa.JSON()),
        sa.UniqueConstraint("case_id", "field_definition_id"),
    )
    op.create_table(
        "case_participants",
        sa.Column("case_id", uuid_type, sa.ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("participant_type", sa.String(30), primary_key=True),
        sa.Column("added_by", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", timestamp, server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "comments",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("case_id", uuid_type, sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("visibility", visibility, nullable=False),
        sa.Column("created_at", timestamp, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", timestamp, server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("actor_id", uuid_type, sa.ForeignKey("users.id")),
        sa.Column("before_json", sa.JSON()),
        sa.Column("after_json", sa.JSON()),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", timestamp, server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "refresh_tokens",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", timestamp, nullable=False),
        sa.Column("revoked_at", timestamp),
        sa.Column("created_at", timestamp, server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "case_number_counters",
        sa.Column("year", sa.Integer(), primary_key=True),
        sa.Column("next_value", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    for table in [
        "case_number_counters",
        "refresh_tokens",
        "audit_events",
        "comments",
        "case_participants",
        "case_field_values",
        "cases",
        "field_definitions",
        "form_definitions",
        "request_types",
        "environment_memberships",
        "group_members",
        "environments",
        "roles",
        "groups",
        "users",
    ]:
        op.drop_table(table)
