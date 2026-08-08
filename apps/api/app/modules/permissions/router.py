import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.modules.access.mapping import codes
from app.modules.access.models import AccessLevelAssignment, PermissionDomain
from app.modules.access.service import replace_levels
from app.modules.api import DB, Current, audit, require
from app.modules.models import (
    Group,
    GroupPermissionAssignment,
    Permission,
    User,
    UserPermissionAssignment,
)

router = APIRouter(prefix="/api/permissions", tags=["permissions"])


class PermissionPatch(BaseModel):
    name_he: str = Field(min_length=2, max_length=160)
    description_he: str = Field(min_length=2)
    category: str = Field(min_length=2, max_length=100)
    is_active: bool


class BulkPermissionIn(BaseModel):
    permission_codes: list[str] = Field(min_length=1)
    environment_id: uuid.UUID | None = None
    operation: Literal["add", "remove", "replace"]
    user_ids: list[uuid.UUID] = Field(default_factory=list)
    group_ids: list[uuid.UUID] = Field(default_factory=list)


def authorize_scope(db: DB, user: Current, environment_id: uuid.UUID | None, rows: list[Permission]) -> None:
    if any(row.scope == "system" for row in rows):
        if not user.is_system_admin:
            raise HTTPException(403, "רק מנהל מערכת רשאי לשייך הרשאה מערכתית")
    else:
        if not environment_id:
            raise HTTPException(422, "יש לבחור סביבה להרשאות סביבתיות")
        require(db, user, environment_id, "environment.users.manage")


def permission_rows(db: DB, codes: list[str]) -> list[Permission]:
    rows = list(db.scalars(select(Permission).where(Permission.code.in_(codes), Permission.is_active.is_(True))))
    if len(rows) != len(set(codes)):
        raise HTTPException(422, "אחת ההרשאות אינה קיימת או אינה פעילה")
    return rows


def apply_bulk(
    db: DB,
    user: Current,
    model: type[Any],
    entity_field: str,
    entity_ids: list[uuid.UUID],
    data: BulkPermissionIn,
) -> dict[str, Any]:
    rows = permission_rows(db, data.permission_codes)
    authorize_scope(db, user, data.environment_id, rows)
    created = removed = unchanged = 0
    for entity_id in entity_ids:
        existing = list(db.scalars(select(model).where(
            getattr(model, entity_field) == entity_id,
            model.environment_id == data.environment_id,
        )))
        indexed = {row.permission_code: row for row in existing}
        if data.operation == "replace":
            for row in existing:
                if row.permission_code not in data.permission_codes:
                    db.delete(row)
                    removed += 1
        for code in data.permission_codes:
            current = indexed.get(code)
            if data.operation == "remove":
                if current:
                    db.delete(current)
                    removed += 1
                else:
                    unchanged += 1
            elif current:
                unchanged += 1
            else:
                db.add(model(**{entity_field: entity_id}, permission_code=code,
                             environment_id=data.environment_id, is_allowed=True, created_by=user.id))
                created += 1
    audit(db, user, "permission_assignment", uuid.uuid4(), f"bulk_{data.operation}",
          after={"entities": [str(value) for value in entity_ids], "permissions": data.permission_codes,
                 "environment_id": str(data.environment_id) if data.environment_id else None,
                 "created": created, "removed": removed, "unchanged": unchanged})
    db.commit()
    return {"created": created, "removed": removed, "unchanged": unchanged, "failed": []}


def sync_access_levels(db: DB, user: Current, subject_type: str, subject_ids: list[uuid.UUID],
                       data: BulkPermissionIn) -> None:
    levels: dict[str, str] = {}
    for domain in db.scalars(select(PermissionDomain).where(PermissionDomain.is_active.is_(True))):
        for permission_code in data.permission_codes:
            if permission_code in codes(domain.edit_permissions):
                levels[domain.code] = "edit"
            elif permission_code in codes(domain.view_permissions) and levels.get(domain.code) != "edit":
                levels[domain.code] = "view"
    if data.operation == "remove":
        field = AccessLevelAssignment.user_id if subject_type == "users" else AccessLevelAssignment.group_id
        for row in db.scalars(select(AccessLevelAssignment).where(
            field.in_(subject_ids), AccessLevelAssignment.environment_id == data.environment_id,
            AccessLevelAssignment.domain_code.in_(levels))):
            db.delete(row)
    else:
        replace_levels(db, user.id, subject_type, subject_ids, data.environment_id, levels)
    db.commit()


@router.get("/manage")
def catalog(db: DB, user: Current) -> list[dict[str, Any]]:
    if not user.is_system_admin:
        raise HTTPException(403, "נדרשת הרשאת מנהל מערכת")
    result = []
    for row in db.scalars(select(Permission).order_by(Permission.category, Permission.name_he)):
        user_count = db.scalar(select(func.count()).select_from(UserPermissionAssignment).where(
            UserPermissionAssignment.permission_code == row.code)) or 0
        group_count = db.scalar(select(func.count()).select_from(GroupPermissionAssignment).where(
            GroupPermissionAssignment.permission_code == row.code)) or 0
        result.append({"code": row.code, "name_he": row.name_he, "description_he": row.description_he,
                       "category": row.category, "scope": row.scope, "is_active": row.is_active,
                       "user_count": user_count, "group_count": group_count})
    return result


@router.patch("/{code}")
def update_permission(code: str, data: PermissionPatch, db: DB, user: Current) -> dict[str, Any]:
    if not user.is_system_admin:
        raise HTTPException(403, "נדרשת הרשאת מנהל מערכת")
    item = db.get(Permission, code)
    if not item:
        raise HTTPException(404, "ההרשאה לא נמצאה")
    before = {"name_he": item.name_he, "description_he": item.description_he,
              "category": item.category, "is_active": item.is_active}
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    audit(db, user, "permission", uuid.uuid5(uuid.NAMESPACE_URL, code), "updated", before, data.model_dump())
    db.commit()
    return {"code": item.code, **data.model_dump(), "scope": item.scope}


@router.post("/bulk/users")
def bulk_users(data: BulkPermissionIn, db: DB, user: Current) -> dict[str, Any]:
    if not data.user_ids:
        raise HTTPException(422, "יש לבחור לפחות משתמש אחד")
    known = set(db.scalars(select(User.id).where(User.id.in_(data.user_ids))))
    if known != set(data.user_ids):
        raise HTTPException(404, "אחד המשתמשים לא נמצא")
    result = apply_bulk(db, user, UserPermissionAssignment, "user_id", data.user_ids, data)
    sync_access_levels(db, user, "users", data.user_ids, data)
    return result


@router.post("/bulk/groups")
def bulk_groups(data: BulkPermissionIn, db: DB, user: Current) -> dict[str, Any]:
    if not data.group_ids:
        raise HTTPException(422, "יש לבחור לפחות קבוצת משתמשים אחת")
    known = set(db.scalars(select(Group.id).where(Group.id.in_(data.group_ids))))
    if known != set(data.group_ids):
        raise HTTPException(404, "אחת הקבוצות לא נמצאה")
    result = apply_bulk(db, user, GroupPermissionAssignment, "group_id", data.group_ids, data)
    sync_access_levels(db, user, "groups", data.group_ids, data)
    return result
