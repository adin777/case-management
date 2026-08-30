import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.modules.api import DB, Current, audit
from app.modules.case_semantics.service import CaseSemanticFieldService
from app.modules.global_case_values.service import active_values, initial_status, model_for, set_initial
from app.modules.models import (
    GlobalCaseFieldOption,
)

router = APIRouter(prefix="/api/global-case-values", tags=["global-case-values"])
Kind = Literal["statuses", "priorities", "sub-priorities"]


class ValueIn(BaseModel):
    label_he: str = Field(min_length=1, max_length=200)
    label_en: str | None = Field(default=None, max_length=200)
    is_active: bool = True
    color: str | None = Field(default=None, max_length=20)
    semantic_category: str = "open"
    is_initial: bool = False
    is_final: bool = False


def admin(user: Current) -> None:
    if not user.is_system_admin:
        raise HTTPException(403, "נדרשת הרשאת מנהל מערכת")


def out(row: Any) -> dict[str, Any]:
    result = {"id": row.id, "code": row.code, "label_he": row.label_he, "label_en": row.label_en,
              "is_active": row.is_active, "sort_order": row.sort_order, "color": row.color}
    if kind := (row.metadata_json or {}).get("semantic_category") if isinstance(row, GlobalCaseFieldOption) else None:
        result.update(semantic_category=kind, is_initial=row.is_initial, is_final=row.is_final)
    return result


@router.get("")
def all_values(db: DB, user: Current) -> dict[str, list[dict[str, Any]]]:
    return {kind: [out(row) for row in active_values(db, kind)] for kind in ("statuses", "priorities", "sub-priorities")}


@router.get("/{kind}")
def list_values(kind: Kind, db: DB, user: Current, include_inactive: bool = False) -> list[dict[str, Any]]:
    if not include_inactive: return [out(row) for row in active_values(db, kind)]
    binding = {"statuses":"case.status","priorities":"case.priority","sub-priorities":"case.sub_priority"}[kind]
    field = CaseSemanticFieldService(db).definition(binding)
    return [out(row) for row in db.scalars(select(GlobalCaseFieldOption).where(
        GlobalCaseFieldOption.global_field_id == field.id).order_by(GlobalCaseFieldOption.sort_order))] if field else []


@router.post("/{kind}", status_code=201)
def create_value(kind: Kind, data: ValueIn, db: DB, user: Current) -> dict[str, Any]:
    admin(user)
    code = f"{kind.replace('-', '_')}_{uuid.uuid4().hex[:12]}"
    binding = {"statuses":"case.status","priorities":"case.priority","sub-priorities":"case.sub_priority"}[kind]
    field = CaseSemanticFieldService(db).definition(binding)
    if not field: raise HTTPException(409, "לא הוגדר שדה גלובלי סמנטי")
    metadata: dict[str, Any] = {"code":code,"color":data.color}
    if kind == "statuses": metadata.update(semantic_category=data.semantic_category,
        is_initial=data.is_initial,is_final=data.is_final)
    row = GlobalCaseFieldOption(id=uuid.uuid4(),global_field_id=field.id,
        label_he=data.label_he.strip(),label_en=data.label_en or "",is_active=data.is_active,
        sort_order=db.scalar(select(func.count()).select_from(GlobalCaseFieldOption).where(
            GlobalCaseFieldOption.global_field_id==field.id)) or 0,metadata_json=metadata)
    db.add(row); db.flush()
    if kind == "statuses" and data.is_initial: set_initial(db, row.id)
    audit(db, user, "global_case_value", row.id, "created", after={"kind": kind, **data.model_dump()})
    db.commit(); return out(row)


@router.patch("/{kind}/{value_id}")
def update_value(kind: Kind, value_id: uuid.UUID, data: ValueIn, db: DB, user: Current) -> dict[str, Any]:
    admin(user); model = model_for(kind); row = db.get(model, value_id)
    if not row: raise HTTPException(404, "הערך לא נמצא")
    if kind == "statuses" and row.is_initial and not data.is_active:
        raise HTTPException(409, "לא ניתן להשבית את הסטטוס ההתחלתי")
    row.label_he, row.label_en, row.is_active = data.label_he.strip(), data.label_en or "", data.is_active
    row.metadata_json = {**(row.metadata_json or {}), "color":data.color}
    if kind == "statuses":
        row.metadata_json = {**row.metadata_json, "semantic_category":data.semantic_category,
                             "is_final":data.is_final}
        if data.is_initial: set_initial(db, row.id)
    audit(db, user, "global_case_value", row.id, "updated", after={"kind": kind, **data.model_dump()})
    db.commit(); return out(row)


@router.post("/statuses/{value_id}/set-initial")
def choose_initial(value_id: uuid.UUID, db: DB, user: Current) -> dict[str, Any]:
    admin(user); row = set_initial(db, value_id); audit(db, user, "global_status", row.id, "set_initial"); db.commit(); return out(row)


@router.put("/{kind}/order")
def reorder(kind: Kind, ids: list[uuid.UUID], db: DB, user: Current) -> list[dict[str, Any]]:
    admin(user); model = model_for(kind); rows = list(db.scalars(select(model).where(model.id.in_(ids))))
    if len(rows) != len(ids): raise HTTPException(422, "סדר הערכים מכיל מזהה לא תקין")
    by_id = {row.id: row for row in rows}
    for index, value_id in enumerate(ids): by_id[value_id].sort_order = index
    db.commit(); return [out(by_id[value_id]) for value_id in ids]


@router.get("/status/initial/current")
def get_initial(db: DB, user: Current) -> dict[str, Any]:
    return out(initial_status(db))
