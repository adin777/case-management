import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from app.modules.access.models import AccessLevelAssignment, PermissionDomain
from app.modules.access.service import replace_levels
from app.modules.api import DB, Current, audit

router = APIRouter(prefix="/api/access", tags=["access"])


class BulkAccessIn(BaseModel):
    subject_type: Literal["users", "groups"]
    subject_ids: list[uuid.UUID] = Field(min_length=1)
    environment_id: uuid.UUID | None = None
    levels: dict[str, Literal["none", "view", "edit"]]


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
    replace_levels(db, user.id, data.subject_type, data.subject_ids, data.environment_id, data.levels)
    audit(db, user, "access_level", uuid.uuid4(), "bulk_updated", after=data.model_dump(mode="json"))
    db.commit()
    return {"subjects": len(data.subject_ids), "domains": len(data.levels)}


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
