import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.modules.api import DB, Current, audit, case_access, permissions, require
from app.modules.models import Case, Environment, RequestType
from app.modules.transfer.service import build_preview, target_requirements, transfer

router = APIRouter(prefix="/api")


class TransferValue(BaseModel):
    field_definition_id: uuid.UUID
    value: Any


class TransferIn(BaseModel):
    target_environment_id: uuid.UUID
    target_request_type_id: uuid.UUID
    target_status_id: uuid.UUID | None = None
    priority_id: uuid.UUID | None = None
    sub_priority_id: uuid.UUID | None = None
    assignee_id: uuid.UUID | None = None
    new_field_values: list[TransferValue] = Field(default_factory=list)
    reason: str | None = Field(default=None, max_length=1000)


def _authorize(db: DB, user: Current, item: Case, target_id: uuid.UUID) -> None:
    case_access(db, user, item)
    require(db, user, item.environment_id, "case.transfer_environment")
    require(db, user, target_id, "case.transfer_environment")
    if item.is_locked and not (
        user.is_system_admin or "environment.manage" in permissions(db, user, item.environment_id)
    ):
        raise HTTPException(403, "הקריאה נעולה ואין הרשאה לעקוף את הנעילה")


@router.get("/cases/{case_id}/transfer-preview")
def preview(case_id: uuid.UUID, db: DB, user: Current, target_environment_id: uuid.UUID) -> dict[str, Any]:
    item = db.get(Case, case_id)
    if not item:
        raise HTTPException(404, "הקריאה לא נמצאה")
    _authorize(db, user, item, target_environment_id)
    return build_preview(db, item, target_environment_id)


@router.get("/cases/{case_id}/transfer-requirements")
def requirements(case_id: uuid.UUID, request_type_id: uuid.UUID, db: DB, user: Current) -> dict[str, Any]:
    item, request_type = db.get(Case, case_id), db.get(RequestType, request_type_id)
    if not item or not request_type:
        raise HTTPException(404, "הקריאה או סוג הקריאה לא נמצאו")
    _authorize(db, user, item, request_type.environment_id)
    return target_requirements(db, item, request_type)


@router.post("/cases/{case_id}/transfer")
def execute(case_id: uuid.UUID, data: TransferIn, db: DB, user: Current) -> dict[str, Any]:
    item = db.get(Case, case_id)
    if not item or not db.get(Environment, data.target_environment_id):
        raise HTTPException(404, "הקריאה או סביבת היעד לא נמצאו")
    _authorize(db, user, item, data.target_environment_id)
    try:
        history = transfer(db, item, user, data)
        audit(
            db,
            user,
            "case",
            item.id,
            "case_environment_transferred",
            {"environment_id": str(history.from_environment_id)},
            {"environment_id": str(history.to_environment_id), "transfer_id": str(history.id)},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {
        "case_id": str(item.id),
        "case_number": item.case_number,
        "environment_id": str(item.environment_id),
        "transfer_id": str(history.id),
    }
