import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from app.modules.access.models import AccessLevelAssignment, PermissionDomain
from app.modules.access.service import EffectivePermissionService, replace_levels
from app.modules.api import DB, Current, audit
from app.modules.models import Group, User

router = APIRouter(prefix="/api/access", tags=["access"])


class BulkAccessIn(BaseModel):
    subject_type: Literal["users", "groups"]
    subject_ids: list[uuid.UUID] = Field(min_length=1)
    environment_id: uuid.UUID | None = None
    levels: dict[str, Literal["inherit", "none", "view", "edit"]]


class CopyAccessIn(BaseModel):
    source_type: Literal["user", "group"]
    source_id: uuid.UUID
    target_type: Literal["users", "groups"]
    target_ids: list[uuid.UUID] = Field(min_length=1)
    environment_id: uuid.UUID | None = None
    mode: Literal["replace", "merge", "missing"] = "replace"


def system_admin(user: Current) -> None:
    if not user.is_system_admin:
        raise HTTPException(403, "נדרשת הרשאת מנהל מערכת")


@router.get("/domains")
def domains(db: DB, user: Current) -> list[dict]:
    system_admin(user)
    rows = db.scalars(select(PermissionDomain).where(PermissionDomain.is_active.is_(True)).order_by(PermissionDomain.sort_order))
    return [{column.name: getattr(row, column.name) for column in row.__table__.columns} for row in rows]


@router.get("/assignments")
def assignments(
    subject_type: Literal["users", "groups"],
    subject_ids: str,
    db: DB,
    user: Current,
    environment_id: uuid.UUID | None = None,
) -> dict:
    system_admin(user)
    ids = [uuid.UUID(value) for value in subject_ids.split(",") if value]
    field = AccessLevelAssignment.user_id if subject_type == "users" else AccessLevelAssignment.group_id
    rows = list(db.scalars(select(AccessLevelAssignment).where(field.in_(ids), AccessLevelAssignment.environment_id == environment_id)))
    by_domain: dict[str, list[str]] = {}
    for row in rows:
        by_domain.setdefault(row.domain_code, []).append(row.access_level)
    return {"levels": {code: values[0] if len(set(values)) == 1 and len(values) == len(ids) else "mixed" for code, values in by_domain.items()}}


@router.post("/bulk")
def bulk(data: BulkAccessIn, db: DB, user: Current) -> dict[str, int]:
    system_admin(user)
    if data.subject_type == "groups" and db.scalar(select(Group.id).where(
        Group.id.in_(data.subject_ids), Group.is_system_admin_group.is_(True))):
        raise HTTPException(409, "קבוצת Admin מקבלת עריכה אוטומטית ואינה תומכת ב־Override")
    aliases = {"users": "users_manage", "groups": "groups_manage", "access": "access_manage"}
    expanded: dict[str, Literal["inherit", "none", "view", "edit"]] = {}
    for code, level in data.levels.items():
        if code == "cases":
            expanded["cases_view"] = level
            if level == "edit":
                expanded["cases_edit"] = "edit"
        else:
            expanded[aliases.get(code, code)] = level
    data.levels = expanded
    known_domains = {row.code: row for row in db.scalars(select(PermissionDomain).where(PermissionDomain.code.in_(data.levels)))}
    if len(known_domains) != len(data.levels):
        raise HTTPException(422, "אחד מתחומי ההרשאה אינו קיים")
    if data.subject_type == "groups" and "inherit" in data.levels.values():
        raise HTTPException(422, "ירושה זמינה רק כחריגת משתמש")
    if data.environment_id and any(row.scope == "global" for row in known_domains.values()):
        raise HTTPException(422, "תחום הרשאה כללי אינו ניתן להגדרה בסביבה")
    replace_levels(db, user.id, data.subject_type, data.subject_ids, data.environment_id, data.levels)
    audit(db, user, "access_level", uuid.uuid4(), "bulk_updated", after=data.model_dump(mode="json"))
    db.commit()
    return {"subjects": len(data.subject_ids), "domains": len(data.levels)}


@router.get("/users/{user_id}/overrides")
def user_overrides(user_id: uuid.UUID, db: DB, user: Current,
                   environment_id: uuid.UUID | None = None) -> dict[str, str]:
    system_admin(user)
    if not db.get(User, user_id):
        raise HTTPException(404, "המשתמש לא נמצא")
    rows = db.scalars(select(AccessLevelAssignment).where(
        AccessLevelAssignment.user_id == user_id,
        AccessLevelAssignment.environment_id == environment_id,
    ))
    return {row.domain_code: row.access_level for row in rows}


@router.get("/users/{user_id}/effective-access")
def effective_access(user_id: uuid.UUID, db: DB, user: Current,
                     environment_id: uuid.UUID | None = None) -> list[dict]:
    if not user.is_system_admin and user.id != user_id:
        raise HTTPException(403, "אין הרשאה לצפייה בהרשאות המשתמש")
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "המשתמש לא נמצא")
    return EffectivePermissionService(db).explain_all(target, environment_id)


@router.get("/subjects/{subject_type}/{subject_id}/matrix")
def subject_matrix(subject_type: Literal["user", "group"], subject_id: uuid.UUID,
                   db: DB, user: Current, environment_id: uuid.UUID | None = None) -> list[dict]:
    system_admin(user)
    domains = list(db.scalars(select(PermissionDomain).where(
        PermissionDomain.is_active.is_(True)).order_by(PermissionDomain.sort_order)))
    field = AccessLevelAssignment.user_id if subject_type == "user" else AccessLevelAssignment.group_id
    subject = db.get(User, subject_id) if subject_type == "user" else db.get(Group, subject_id)
    if not subject:
        raise HTTPException(404, "המשתמש או הקבוצה לא נמצאו")
    direct = {row.domain_code: row.access_level for row in db.scalars(select(AccessLevelAssignment).where(
        field == subject_id, AccessLevelAssignment.environment_id == environment_id))}
    if subject_type == "user":
        target = db.get(User, subject_id)
        if not target:
            raise HTTPException(404, "המשתמש לא נמצא")
        resolved = {row["domain"]: row for row in EffectivePermissionService(db).explain_all(target, environment_id)}
        return [{"domain_code": domain.code, "domain_name": domain.name_he,
                 "description": domain.description_he,
                 "direct_level": direct.get(domain.code, "inherit"),
                 "effective_level": resolved[domain.code]["effective_level"],
                 "source": resolved[domain.code]["source_name"], "scope": domain.scope,
                 "can_override": not target.is_system_admin} for domain in domains]
    if isinstance(subject, Group) and subject.is_system_admin_group:
        return [{"domain_code": domain.code, "domain_name": domain.name_he,
                 "description": domain.description_he,
                 "direct_level": "none", "effective_level": "edit", "source": "קבוצת Admin",
                 "scope": domain.scope, "can_override": False} for domain in domains]
    return [{"domain_code": domain.code, "domain_name": domain.name_he,
             "description": domain.description_he,
             "direct_level": direct.get(domain.code, "none"),
             "effective_level": direct.get(domain.code, "none"),
             "source": "הרשאת קבוצה" if domain.code in direct else "אין הרשאה",
             "scope": domain.scope, "can_override": True} for domain in domains]


def source_levels(db: DB, data: CopyAccessIn) -> dict[str, str]:
    field = AccessLevelAssignment.user_id if data.source_type == "user" else AccessLevelAssignment.group_id
    return {row.domain_code: row.access_level for row in db.scalars(select(AccessLevelAssignment).where(field == data.source_id, AccessLevelAssignment.environment_id == data.environment_id))}


@router.post("/copy/preview")
def copy_preview(data: CopyAccessIn, db: DB, user: Current) -> dict:
    system_admin(user)
    levels = source_levels(db, data)
    return {"source_levels": levels, "targets": len(data.target_ids), "mode": data.mode, "environment_id": data.environment_id}


@router.post("/copy")
def copy_access(data: CopyAccessIn, db: DB, user: Current) -> dict[str, int]:
    system_admin(user)
    levels = source_levels(db, data)
    target_field = AccessLevelAssignment.user_id if data.target_type == "users" else AccessLevelAssignment.group_id
    if data.mode == "replace":
        db.execute(delete(AccessLevelAssignment).where(target_field.in_(data.target_ids), AccessLevelAssignment.environment_id == data.environment_id))
    elif data.mode == "missing":
        existing = set(db.scalars(select(AccessLevelAssignment.domain_code).where(target_field.in_(data.target_ids), AccessLevelAssignment.environment_id == data.environment_id)))
        levels = {code: level for code, level in levels.items() if code not in existing}
    replace_levels(db, user.id, data.target_type, data.target_ids, data.environment_id, levels)
    audit(db, user, "access_level", uuid.uuid4(), "copied", after=data.model_dump(mode="json") | {"levels": levels})
    db.commit()
    return {"targets": len(data.target_ids), "domains": len(levels)}
