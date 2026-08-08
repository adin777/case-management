"""Unify environment field metadata and independent sub-priorities.

Revision ID: 0010
Revises: 0009
"""

import sqlalchemy as sa

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("roles") as batch:
        batch.add_column(sa.Column("system_number", sa.String(40), nullable=True))
        batch.add_column(sa.Column("name_he", sa.String(120), nullable=True))
        batch.add_column(sa.Column("description_he", sa.Text(), nullable=True))
        batch.add_column(sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
        batch.create_unique_constraint("uq_roles_system_number", ["system_number"])
    op.execute("UPDATE roles SET name_he = name WHERE name_he IS NULL")

    with op.batch_alter_table("request_types") as batch:
        batch.add_column(sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.false()))
    with op.batch_alter_table("environment_memberships") as batch:
        batch.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))

    with op.batch_alter_table("sub_priority_definitions") as batch:
        batch.add_column(sa.Column("environment_id", sa.Uuid(), nullable=True))
        batch.alter_column("priority_id", existing_type=sa.Uuid(), nullable=True)
        batch.create_foreign_key("fk_sub_priority_environment", "environments", ["environment_id"], ["id"])
        batch.create_index("ix_sub_priority_environment", ["environment_id"])
    op.execute("""
        UPDATE sub_priority_definitions
        SET environment_id = (
            SELECT priority_definitions.environment_id
            FROM priority_definitions
            WHERE priority_definitions.id = sub_priority_definitions.priority_id
        )
    """)

    with op.batch_alter_table("approval_flow_definitions") as batch:
        batch.add_column(sa.Column("approval_policy", sa.String(40), nullable=False,
                                   server_default="all_active_steps"))
    with op.batch_alter_table("approval_instances") as batch:
        batch.add_column(sa.Column("request_type_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("approval_policy", sa.String(40), nullable=False,
                                   server_default="all_active_steps"))
        batch.create_foreign_key("fk_approval_instance_request_type", "request_types",
                                 ["request_type_id"], ["id"])
    op.execute("""
        UPDATE approval_instances
        SET request_type_id = (
            SELECT cases.request_type_id FROM cases WHERE cases.id = approval_instances.case_id
        )
    """)


def downgrade() -> None:
    with op.batch_alter_table("approval_instances") as batch:
        batch.drop_constraint("fk_approval_instance_request_type", type_="foreignkey")
        batch.drop_column("approval_policy")
        batch.drop_column("request_type_id")
    with op.batch_alter_table("approval_flow_definitions") as batch:
        batch.drop_column("approval_policy")
    with op.batch_alter_table("sub_priority_definitions") as batch:
        batch.drop_index("ix_sub_priority_environment")
        batch.drop_constraint("fk_sub_priority_environment", type_="foreignkey")
        batch.alter_column("priority_id", existing_type=sa.Uuid(), nullable=False)
        batch.drop_column("environment_id")
    with op.batch_alter_table("request_types") as batch:
        batch.drop_column("requires_approval")
        batch.drop_column("sort_order")
    with op.batch_alter_table("environment_memberships") as batch:
        batch.drop_column("is_active")
    with op.batch_alter_table("roles") as batch:
        batch.drop_constraint("uq_roles_system_number", type_="unique")
        batch.drop_column("sort_order")
        batch.drop_column("description_he")
        batch.drop_column("name_he")
        batch.drop_column("system_number")
