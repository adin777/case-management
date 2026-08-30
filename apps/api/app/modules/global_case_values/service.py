import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.case_semantics.service import CaseSemanticFieldService
from app.modules.models import GlobalCaseFieldOption

BINDINGS = {"statuses":"case.status", "priorities":"case.priority",
            "sub-priorities":"case.sub_priority"}


def model_for(kind: str) -> Any:
    if kind not in BINDINGS: raise HTTPException(404, "קטלוג ערכים לא נמצא")
    return GlobalCaseFieldOption


def active_values(db: Session, kind: str) -> list[GlobalCaseFieldOption]:
    binding = BINDINGS.get(kind)
    field = CaseSemanticFieldService(db).definition(binding or "")
    if not field: return []
    return list(db.scalars(select(GlobalCaseFieldOption).where(
        GlobalCaseFieldOption.global_field_id == field.id,
        GlobalCaseFieldOption.is_active.is_(True)).order_by(
            GlobalCaseFieldOption.sort_order, GlobalCaseFieldOption.label_he)))


def initial_status(db: Session) -> GlobalCaseFieldOption:
    row = next((item for item in active_values(db, "statuses") if item.is_initial), None)
    if not row:
        raise HTTPException(409, {"code":"GLOBAL_INITIAL_STATUS_MISSING",
            "message":"לא הוגדר סטטוס התחלתי גלובלי", "settings_path":"/admin/case-values"})
    return row


def set_initial(db: Session, status_id: uuid.UUID) -> GlobalCaseFieldOption:
    rows = active_values(db, "statuses"); row = next((item for item in rows if item.id == status_id), None)
    if not row: raise HTTPException(422, "רק סטטוס פעיל יכול להיות התחלתי")
    for item in rows:
        item.metadata_json = {**(item.metadata_json or {}), "is_initial":item.id == status_id}
    return row
