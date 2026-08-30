import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.case_semantics.service import CaseSemanticFieldService
from app.modules.models import (
    CaseFieldDefinition,
    GlobalCaseFieldDefinition,
    Group,
    RequestType,
    User,
)
from app.modules.system_fields.registry import BY_CODE


def options_for(db: Session, environment_id: uuid.UUID, field_code: str,
                *, active_only: bool = True) -> list[dict[str, Any]]:
    try:
        stable_id = uuid.UUID(field_code)
    except ValueError:
        stable_id = None
    if stable_id:
        global_field = db.get(GlobalCaseFieldDefinition, stable_id)
        if global_field and global_field.is_active:
            if global_field.field_type == "user":
                user_rows = db.scalars(select(User).where(User.is_active.is_(True)).order_by(User.display_name))
                return [{"id": row.id, "label_he": row.display_name} for row in user_rows]
            return [{"id": row["id"], "label_he": row["label_he"]}
                    for row in CaseSemanticFieldService(db).options_for_field(stable_id,
                                                                              active_only=active_only)]
        environment_field = db.get(CaseFieldDefinition, stable_id)
        if environment_field and environment_field.environment_id == environment_id and environment_field.is_active:
            return [{"id": option.get("value"), "label_he": option.get("label_he") or option.get("value")}
                    for option in (environment_field.options_json or []) if option.get("is_active", True)]
        raise HTTPException(404, "השדה לא נמצא")
    if field_code not in BY_CODE and not field_code.startswith("dynamic:"):
        raise HTTPException(404, "שדה המערכת לא נמצא")
    if field_code == "request_type":
        request_query = select(RequestType).where(RequestType.environment_id == environment_id)
        if active_only: request_query = request_query.where(RequestType.is_active.is_(True))
        request_rows = db.scalars(request_query.order_by(RequestType.sort_order, RequestType.name_he))
        return [{"id": row.id, "code": row.code, "label_he": row.name_he, "description": row.description,
                 "sort_order": row.sort_order, "is_active": row.is_active,
                 "requires_approval": row.requires_approval,
                 "workflow_id": row.workflow_definition_id,
                 "default_priority_id": row.default_priority_id,
                 "default_sub_priority_id": row.default_sub_priority_id,
                 "default_assignee_user_id": row.default_assignee_user_id,
                 "default_assignee_group_id": row.default_assignee_group_id} for row in request_rows]
    semantic_binding = {"status": "case.status", "priority": "case.priority",
                        "sub_priority": "case.sub_priority"}.get(field_code)
    if semantic_binding:
        rows = CaseSemanticFieldService(db).option_rows(semantic_binding, active_only=active_only)
        result = [{"id": row.id, "code": row.code, "label_he": row.label_he, "color": row.color,
                 "sort_order": row.sort_order, "is_active": row.is_active,
                 } for row in rows]
        if field_code == "status":
            for item, row in zip(result, rows, strict=True):
                item.update(is_initial=row.is_initial, is_final=row.is_final,
                            semantic_category=row.semantic_category, workflow_id=None)
        return result
    if field_code in {"assignee", "participants"}:
        user_rows = db.scalars(select(User).where(User.is_active.is_(True)).order_by(User.display_name))
        return [{"id": row.id, "label_he": row.display_name} for row in user_rows]
    if field_code == "assignee_group":
        group_rows = db.scalars(select(Group).where(Group.is_active.is_(True)).order_by(Group.name))
        return [{"id": row.id, "label_he": row.name} for row in group_rows]
    if field_code.startswith("dynamic:"):
        field_id = uuid.UUID(field_code.split(":", 1)[1])
        field = db.get(CaseFieldDefinition, field_id)
        if not field or field.environment_id != environment_id or not field.is_active:
            raise HTTPException(404, "השדה הדינמי לא נמצא")
        return [{"id": option.get("value"), "label_he": option.get("label_he") or option.get("value")}
                for option in field.options_json if option.get("is_active", True)]
    return []
