"""Unify effective permission resolution on access-level assignments.

Revision ID: 0013
Revises: 0012
"""

from collections.abc import Sequence
import json
import uuid

import sqlalchemy as sa
from alembic import op
from app.modules.access.mapping import DOMAIN_DEFINITIONS

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _codes(value: str | None) -> set[str]:
    return {item.strip() for item in (value or "").split(",") if item.strip()}


def upgrade() -> None:
    with op.batch_alter_table("permission_domains") as batch:
        batch.add_column(sa.Column("category", sa.String(100), nullable=False, server_default="מערכת"))

    connection = op.get_bind()
    active_codes: list[str] = []
    for order, definition in enumerate(DOMAIN_DEFINITIONS):
        code, name, description, category, scope, view_codes, edit_codes = definition
        active_codes.append(code)
        current = connection.execute(sa.text(
            "select code from permission_domains where code = :code"
        ), {"code": code}).first()
        values = {"code": code, "name": name, "description": description, "category": category,
                  "scope": scope, "view_codes": view_codes, "edit_codes": edit_codes, "sort_order": order}
        if current:
            connection.execute(sa.text(
                "update permission_domains set name_he=:name, description_he=:description, category=:category, "
                "scope=:scope, view_permissions=:view_codes, edit_permissions=:edit_codes, "
                "sort_order=:sort_order, is_active=1 where code=:code"
            ), values)
        else:
            connection.execute(sa.text(
                "insert into permission_domains (code,name_he,description_he,category,scope,view_permissions,"
                "edit_permissions,sort_order,is_active) values (:code,:name,:description,:category,:scope,"
                ":view_codes,:edit_codes,:sort_order,1)"
            ), values)
    if active_codes:
        placeholders = ",".join(f":code_{index}" for index in range(len(active_codes)))
        connection.execute(sa.text(
            f"update permission_domains set is_active=0 where code not in ({placeholders})"
        ), {f"code_{index}": code for index, code in enumerate(active_codes)})
    domains = connection.execute(sa.text(
        "select code, view_permissions, edit_permissions from permission_domains"
    )).mappings().all()
    permissions_to_domains: dict[str, list[tuple[str, str]]] = {}
    for domain in domains:
        if domain["code"] not in active_codes:
            continue
        for permission in _codes(domain["view_permissions"]):
            permissions_to_domains.setdefault(permission, []).append((domain["code"], "view"))
        for permission in _codes(domain["edit_permissions"]):
            permissions_to_domains.setdefault(permission, []).append((domain["code"], "edit"))

    existing = {
        (row["domain_code"], row["user_id"], row["group_id"], row["environment_id"])
        for row in connection.execute(sa.text(
            "select domain_code, user_id, group_id, environment_id from access_level_assignments"
        )).mappings()
    }
    candidates: dict[tuple, str] = {}
    domain_index = {row["code"]: row for row in domains}
    legacy_access = connection.execute(sa.text(
        "select domain_code,user_id,group_id,environment_id,access_level,created_by "
        "from access_level_assignments"
    )).mappings()
    for row in legacy_access:
        old_domain = domain_index.get(row["domain_code"])
        if not old_domain or row["domain_code"] in active_codes:
            continue
        permission_codes = _codes(old_domain["view_permissions"])
        if row["access_level"] == "edit":
            permission_codes |= _codes(old_domain["edit_permissions"])
        for permission in permission_codes:
            for domain_code, mapped_level in permissions_to_domains.get(permission, []):
                level = "none" if row["access_level"] == "none" else mapped_level
                key = (domain_code, row["user_id"], row["group_id"],
                       row["environment_id"], row["created_by"])
                previous = candidates.get(key)
                if previous != "none":
                    candidates[key] = level if previous is None or level == "none" or level == "edit" else previous
    actor_id = connection.execute(sa.text(
        "select id from users order by is_system_admin desc, created_at asc limit 1"
    )).scalar()
    role_codes: dict[object, set[str]] = {}
    for role in connection.execute(sa.text("select id, permissions from roles")).mappings():
        try:
            role_codes[role["id"]] = set(json.loads(role["permissions"] or "[]"))
        except (TypeError, ValueError):
            role_codes[role["id"]] = set()
    for row in connection.execute(sa.text("select role_id, permission_code from role_permissions")).mappings():
        role_codes.setdefault(row["role_id"], set()).add(row["permission_code"])
    role_subjects = connection.execute(sa.text(
        "select user_id, null as group_id, environment_id, role_id from environment_memberships "
        "union all select null as user_id, group_id, environment_id, role_id from group_environment_roles"
    )).mappings()
    for row in role_subjects:
        levels: dict[str, str] = {}
        for permission in role_codes.get(row["role_id"], set()):
            for domain_code, mapped_level in permissions_to_domains.get(permission, []):
                if mapped_level == "edit" or domain_code not in levels:
                    levels[domain_code] = mapped_level
        for domain_code, level in levels.items():
            key = (domain_code, row["user_id"], row["group_id"], row["environment_id"],
                   row["user_id"] or actor_id)
            previous = candidates.get(key)
            if previous != "none":
                candidates[key] = level if previous is None or level == "edit" else previous
    for table, subject_column in (("user_permission_assignments", "user_id"),
                                  ("group_permission_assignments", "group_id")):
        rows = connection.execute(sa.text(
            f"select {subject_column} as subject_id, permission_code, environment_id, "
            f"is_allowed, created_by from {table}"
        )).mappings()
        for row in rows:
            for domain_code, mapped_level in permissions_to_domains.get(row["permission_code"], []):
                level = mapped_level if row["is_allowed"] else "none"
                key = (domain_code, row["subject_id"] if subject_column == "user_id" else None,
                       row["subject_id"] if subject_column == "group_id" else None,
                       row["environment_id"], row["created_by"])
                previous = candidates.get(key)
                if previous != "none":
                    candidates[key] = level if previous is None or level == "none" or level == "edit" else previous
    for (domain_code, user_id, group_id, environment_id, created_by), level in candidates.items():
        identity = (domain_code, user_id, group_id, environment_id)
        if identity in existing:
            continue
        connection.execute(sa.text(
            "insert into access_level_assignments "
            "(id, domain_code, user_id, group_id, environment_id, access_level, created_by) "
            "values (:id, :domain, :user_id, :group_id, :environment_id, :level, :created_by)"
        ), {"id": uuid.uuid4().hex, "domain": domain_code, "user_id": user_id,
            "group_id": group_id, "environment_id": environment_id,
            "level": level, "created_by": created_by})

    op.create_index("ux_access_user_global", "access_level_assignments",
                    ["domain_code", "user_id"], unique=True,
                    sqlite_where=sa.text("user_id is not null and environment_id is null"),
                    postgresql_where=sa.text("user_id is not null and environment_id is null"))
    op.create_index("ux_access_group_global", "access_level_assignments",
                    ["domain_code", "group_id"], unique=True,
                    sqlite_where=sa.text("group_id is not null and environment_id is null"),
                    postgresql_where=sa.text("group_id is not null and environment_id is null"))


def downgrade() -> None:
    op.drop_index("ux_access_group_global", table_name="access_level_assignments")
    op.drop_index("ux_access_user_global", table_name="access_level_assignments")
    with op.batch_alter_table("permission_domains") as batch:
        batch.drop_column("category")
