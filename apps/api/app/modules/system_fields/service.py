import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.models import (
    CaseFieldDefinition,
    Group,
    PriorityDefinition,
    RequestType,
    SubPriorityDefinition,
    User,
)
from app.modules.operations.models import WorkflowDefinition, WorkflowStatus
from app.modules.system_fields.registry import BY_CODE


def options_for(db: Session, environment_id: uuid.UUID, field_code: str,
                *, active_only: bool = True) -> list[dict[str, Any]]:
    if field_code not in BY_CODE and not field_code.startswith("dynamic:"):
        raise HTTPException(404, "שדה המערכת לא נמצא")
    if field_code == "request_type":
        request_query = select(RequestType).where(RequestType.environment_id == environment_id)
        if active_only: request_query = request_query.where(RequestType.is_active.is_(True))
        request_rows = db.scalars(request_query.order_by(RequestType.sort_order, RequestType.name_he))
        return [{"id": row.id, "label_he": row.name_he, "description": row.description,
                 "sort_order": row.sort_order, "is_active": row.is_active,
                 "requires_approval": row.requires_approval,
                 "workflow_id": row.workflow_definition_id,
                 "default_priority_id": row.default_priority_id,
                 "default_sub_priority_id": row.default_sub_priority_id,
                 "default_assignee_user_id": row.default_assignee_user_id,
                 "default_assignee_group_id": row.default_assignee_group_id} for row in request_rows]
    if field_code == "status":
        status_query = select(WorkflowStatus).join(WorkflowDefinition).where(
            WorkflowDefinition.environment_id == environment_id, WorkflowDefinition.is_active.is_(True))
        if active_only: status_query = status_query.where(WorkflowStatus.is_active.is_(True))
        status_rows = db.scalars(status_query.order_by(WorkflowStatus.sort_order))
        return [{"id": row.id, "label_he": row.label_he, "color": row.color,
                 "sort_order": row.sort_order, "is_active": row.is_active,
                 "is_initial": row.is_initial, "is_final": row.is_final,
                 "workflow_id": row.workflow_id} for row in status_rows]
    if field_code == "priority":
        priority_query = select(PriorityDefinition).where(PriorityDefinition.environment_id == environment_id)
        if active_only: priority_query = priority_query.where(PriorityDefinition.is_active.is_(True))
        priority_rows = db.scalars(priority_query.order_by(PriorityDefinition.sort_order))
        return [{"id": row.id, "label_he": row.label_he, "color": row.color,
                 "sort_order": row.sort_order, "is_active": row.is_active} for row in priority_rows]
    if field_code == "sub_priority":
        sub_query = select(SubPriorityDefinition).where(SubPriorityDefinition.environment_id == environment_id)
        if active_only: sub_query = sub_query.where(SubPriorityDefinition.is_active.is_(True))
        sub_rows = db.scalars(sub_query.order_by(SubPriorityDefinition.sort_order))
        return [{"id": row.id, "label_he": row.label_he, "color": row.color,
                 "sort_order": row.sort_order, "is_active": row.is_active} for row in sub_rows]
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
