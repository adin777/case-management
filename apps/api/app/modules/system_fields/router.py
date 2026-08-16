import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update

from app.modules.api import DB, Current, audit, require
from app.modules.models import (
    CaseFieldDefinition,
    GlobalPriorityDefinition,
    GlobalStatusDefinition,
    GlobalSubPriorityDefinition,
    RequestType,
)
from app.modules.system_fields.registry import registry_payload
from app.modules.system_fields.service import options_for

router = APIRouter(prefix="/api/environments/{environment_id}", tags=["system-fields"])


class ReorderIn(BaseModel):
    ids: list[uuid.UUID]


@router.put("/system-fields/{field_code}/reorder")
def reorder_system_field(environment_id: uuid.UUID, field_code: str, data: ReorderIn,
                         db: DB, user: Current) -> dict[str, bool]:
    permission = "workflow.manage" if field_code == "status" else "request_type.manage" if field_code == "request_type" else "environment.manage"
    require(db, user, environment_id, permission)
    model: Any = {"request_type": RequestType, "priority": GlobalPriorityDefinition,
                  "sub_priority": GlobalSubPriorityDefinition, "status": GlobalStatusDefinition}.get(field_code)
    if not model:
        raise HTTPException(404, "שדה המערכת אינו תומך בסידור")
    if field_code == "request_type":
        valid_ids = set(db.scalars(select(model.id).where(model.environment_id == environment_id)))
    else:
        valid_ids = set(db.scalars(select(model.id)))
    if set(data.ids) != valid_ids or len(data.ids) != len(valid_ids):
        raise HTTPException(422, "רשימת הסידור אינה תואמת לערכי הסביבה")
    for order, item_id in enumerate(data.ids):
        db.execute(update(model).where(model.id == item_id).values(sort_order=order))
    audit(db, user, f"system_field:{field_code}", environment_id, "reordered")
    db.commit()
    return {"ok": True}


@router.get("/system-fields")
def system_fields(environment_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    require(db, user, environment_id, "environment.read")
    fields = registry_payload()
    for field in fields:
        field["options"] = options_for(db, environment_id, field["code"], active_only=False) if field["supports_options"] else []
        field["active_option_count"] = sum(option.get("is_active", True) for option in field["options"])
    return fields


@router.get("/automation-fields")
def automation_fields(environment_id: uuid.UUID, db: DB, user: Current) -> dict[str, Any]:
    require(db, user, environment_id, "environment.rules.manage")
    core = registry_payload()
    dynamic = [{"code": f"dynamic:{row.id}", "label_he": row.label_he,
                "field_type": row.field_type, "value_source": "CaseFieldDefinition",
                "is_target": True}
               for row in db.scalars(select(CaseFieldDefinition).where(
                   CaseFieldDefinition.environment_id == environment_id,
                   CaseFieldDefinition.is_active.is_(True)).order_by(CaseFieldDefinition.sort_order))]
    normalized = [{"code": row["code"], "label_he": row["label_he"], "field_type": "select",
                   "value_source": row["value_source"], "is_target": row["is_target"]} for row in core]
    return {"trigger_fields": normalized + dynamic,
            "target_fields": [row for row in normalized + dynamic if row["is_target"]]}


@router.get("/automation-fields/{field_code}/options")
def automation_options(environment_id: uuid.UUID, field_code: str, db: DB, user: Current) -> list[dict[str, Any]]:
    require(db, user, environment_id, "environment.rules.manage")
    return options_for(db, environment_id, field_code)
