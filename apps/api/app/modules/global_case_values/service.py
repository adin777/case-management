import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.modules.models import (
    GlobalPriorityDefinition,
    GlobalStatusDefinition,
    GlobalSubPriorityDefinition,
)

CATALOGS: dict[str, type[GlobalStatusDefinition] | type[GlobalPriorityDefinition] | type[GlobalSubPriorityDefinition]] = {
    "statuses": GlobalStatusDefinition,
    "priorities": GlobalPriorityDefinition,
    "sub-priorities": GlobalSubPriorityDefinition,
}


def model_for(kind: str) -> Any:
    model = CATALOGS.get(kind)
    if not model:
        raise HTTPException(404, "קטלוג ערכים לא נמצא")
    return model


def active_values(db: Session, kind: str) -> list[Any]:
    model = model_for(kind)
    return list(db.scalars(select(model).where(model.is_active.is_(True)).order_by(model.sort_order, model.label_he)))


def initial_status(db: Session) -> GlobalStatusDefinition:
    row = db.scalar(select(GlobalStatusDefinition).where(
        GlobalStatusDefinition.is_active.is_(True), GlobalStatusDefinition.is_initial.is_(True)
    ))
    if not row:
        raise HTTPException(409, {"code": "GLOBAL_INITIAL_STATUS_MISSING", "message": "לא הוגדר סטטוס התחלתי גלובלי", "settings_path": "/admin/case-values"})
    return row


def set_initial(db: Session, status_id: uuid.UUID) -> GlobalStatusDefinition:
    row = db.get(GlobalStatusDefinition, status_id)
    if not row or not row.is_active:
        raise HTTPException(422, "רק סטטוס פעיל יכול להיות התחלתי")
    db.execute(update(GlobalStatusDefinition).values(is_initial=False))
    row.is_initial = True
    return row
