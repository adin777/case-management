import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.modules.api import DB, Current, audit
from app.modules.global_case_values.service import active_values, initial_status, model_for, set_initial
from app.modules.models import (
    Environment,
    GlobalPriorityDefinition,
    GlobalStatusDefinition,
    GlobalSubPriorityDefinition,
    PriorityDefinition,
    SubPriorityDefinition,
)
from app.modules.operations.models import WorkflowDefinition, WorkflowStatus

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
    if isinstance(row, GlobalStatusDefinition):
        result.update(semantic_category=row.semantic_category, is_initial=row.is_initial, is_final=row.is_final)
    return result


@router.get("")
def all_values(db: DB, user: Current) -> dict[str, list[dict[str, Any]]]:
    return {kind: [out(row) for row in active_values(db, kind)] for kind in ("statuses", "priorities", "sub-priorities")}


@router.get("/{kind}")
def list_values(kind: Kind, db: DB, user: Current, include_inactive: bool = False) -> list[dict[str, Any]]:
    model = model_for(kind)
    query = select(model).order_by(model.sort_order, model.label_he)
    if not include_inactive: query = query.where(model.is_active.is_(True))
    return [out(row) for row in db.scalars(query)]


@router.post("/{kind}", status_code=201)
def create_value(kind: Kind, data: ValueIn, db: DB, user: Current) -> dict[str, Any]:
    admin(user); model = model_for(kind)
    code = f"{kind.replace('-', '_')}_{uuid.uuid4().hex[:12]}"
    row = model(code=code, label_he=data.label_he.strip(), label_en=data.label_en, is_active=data.is_active,
                color=data.color, sort_order=db.scalar(select(func.count()).select_from(model)) or 0)
    if isinstance(row, GlobalStatusDefinition):
        row.semantic_category, row.is_final = data.semantic_category, data.is_final
    db.add(row); db.flush()
    # Temporary mirrors preserve legacy foreign keys; active reads never use these rows.
    if isinstance(row, GlobalPriorityDefinition):
        environment_id = db.scalar(select(Environment.id).order_by(Environment.created_at))
        if environment_id:
            db.add(PriorityDefinition(id=row.id, environment_id=environment_id, code=row.code,
                label_he=row.label_he, label_en=row.label_en, color=row.color or "#64748b",
                sort_order=row.sort_order, is_active=row.is_active))
    elif isinstance(row, GlobalSubPriorityDefinition):
        environment_id = db.scalar(select(Environment.id).order_by(Environment.created_at))
        if environment_id:
            db.add(SubPriorityDefinition(id=row.id, environment_id=environment_id, priority_id=None,
                code=row.code, label_he=row.label_he, label_en=row.label_en,
                color=row.color or "#64748b", sort_order=row.sort_order, is_active=row.is_active))
    elif isinstance(row, GlobalStatusDefinition):
        workflow_id = db.scalar(select(WorkflowDefinition.id).order_by(WorkflowDefinition.created_at))
        if workflow_id:
            db.add(WorkflowStatus(id=row.id, workflow_id=workflow_id, code=row.code,
                label_he=row.label_he, label_en=row.label_en, color=row.color or "#64748b",
                sort_order=row.sort_order, semantic_category=row.semantic_category,
                is_initial=False, is_final=row.is_final, is_closed=row.semantic_category == "closed",
                is_active=row.is_active))
    if isinstance(row, GlobalStatusDefinition) and data.is_initial: set_initial(db, row.id)
    audit(db, user, "global_case_value", row.id, "created", after={"kind": kind, **data.model_dump()})
    db.commit(); return out(row)


@router.patch("/{kind}/{value_id}")
def update_value(kind: Kind, value_id: uuid.UUID, data: ValueIn, db: DB, user: Current) -> dict[str, Any]:
    admin(user); model = model_for(kind); row = db.get(model, value_id)
    if not row: raise HTTPException(404, "הערך לא נמצא")
    if isinstance(row, GlobalStatusDefinition) and row.is_initial and not data.is_active:
        raise HTTPException(409, "לא ניתן להשבית את הסטטוס ההתחלתי")
    row.label_he, row.label_en, row.is_active, row.color = data.label_he.strip(), data.label_en, data.is_active, data.color
    if isinstance(row, GlobalStatusDefinition):
        row.semantic_category, row.is_final = data.semantic_category, data.is_final
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
