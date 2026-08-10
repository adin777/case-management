"""Add environment numbering, employee identity and scoped user fields.

Revision ID: 0019
Revises: 0018
"""
import uuid

import sqlalchemy as sa

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("environments", sa.Column("system_number", sa.String(40)))
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id FROM environments ORDER BY created_at, id")).fetchall()
    for index, row in enumerate(rows, 1):
        bind.execute(sa.text("UPDATE environments SET system_number=:number WHERE id=:id"),
                     {"number": f"ENV-{index:06d}", "id": row[0]})
    op.create_index("ix_environments_system_number", "environments", ["system_number"], unique=True)
    op.create_table("employees",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("first_name", sa.String(120)),
        sa.Column("last_name", sa.String(120)), sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(320), nullable=False, unique=True), sa.Column("department", sa.String(200)),
        sa.Column("job_title", sa.String(200)), sa.Column("phone", sa.String(80)),
        sa.Column("mobile_phone", sa.String(80)), sa.Column("employee_number", sa.String(120), unique=True),
        sa.Column("computer_identifier", sa.String(200)), sa.Column("directory_object_id", sa.String(200), unique=True),
        sa.Column("source", sa.String(30), nullable=False, server_default="manual"),
        sa.Column("directory_data_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("archived_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_employees_email", "employees", ["email"], unique=True)
    op.create_index("ix_employees_department", "employees", ["department"])
    op.create_index("ix_employees_job_title", "employees", ["job_title"])
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("employee_record_id", sa.Uuid()))
        batch.create_foreign_key("fk_users_employee_record_id", "employees", ["employee_record_id"], ["id"])
        batch.create_unique_constraint("uq_users_employee_record_id", ["employee_record_id"])
    users = bind.execute(sa.text("SELECT id,email,display_name,first_name,last_name,department,job_title,phone,mobile_phone,employee_id,computer_identifier,directory_object_id,source,status,archived_at FROM users")).fetchall()
    for user in users:
        employee_id = str(uuid.uuid4())
        bind.execute(sa.text("INSERT INTO employees (id,email,display_name,first_name,last_name,department,job_title,phone,mobile_phone,employee_number,computer_identifier,directory_object_id,source,status,archived_at,directory_data_json) VALUES (:eid,:email,:display,:first,:last,:department,:job,:phone,:mobile,:number,:computer,:directory,:source,:status,:archived,'{}')"),
            {"eid": employee_id, "email": user[1], "display": user[2], "first": user[3], "last": user[4], "department": user[5], "job": user[6], "phone": user[7], "mobile": user[8], "number": user[9], "computer": user[10], "directory": user[11], "source": user[12], "status": user[13], "archived": user[14]})
        bind.execute(sa.text("UPDATE users SET employee_record_id=:eid WHERE id=:uid"), {"eid": employee_id, "uid": user[0]})
    op.add_column("user_field_definitions", sa.Column("scope", sa.String(20), nullable=False, server_default="global"))
    with op.batch_alter_table("user_field_definitions") as batch:
        batch.add_column(sa.Column("environment_id", sa.Uuid()))
        batch.create_foreign_key("fk_user_fields_environment_id", "environments", ["environment_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("user_field_definitions") as batch:
        batch.drop_constraint("fk_user_fields_environment_id", type_="foreignkey")
        batch.drop_column("environment_id")
        batch.drop_column("scope")
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("uq_users_employee_record_id", type_="unique")
        batch.drop_constraint("fk_users_employee_record_id", type_="foreignkey")
        batch.drop_column("employee_record_id")
    op.drop_table("employees")
    op.drop_index("ix_environments_system_number", "environments")
    op.drop_column("environments", "system_number")
