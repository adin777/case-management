import uuid
from typing import Any

from fastapi import APIRouter
from sqlalchemy import select

from app.modules.api import DB, Current, require
from app.modules.models import CaseFieldDefinition
from app.modules.system_fields.registry import registry_payload
from app.modules.system_fields.service import options_for

router = APIRouter(prefix="/api/environments/{environment_id}", tags=["system-fields"])


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
