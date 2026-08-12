import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.approvals.service import start_matching_approvals
from app.modules.automation.service import AutomationEngine
from app.modules.models import (
    ApprovalInstance,
    ApprovalTask,
    Case,
    CaseFieldValue,
    CaseParticipant,
    CaseTransferHistory,
    Environment,
    EnvironmentMembership,
    FieldDefinition,
    PriorityDefinition,
    RequestType,
    SubPriorityDefinition,
    User,
)
from app.modules.operations.service import initialize_operations, resolve_workflow

VALUE_COLUMNS = (
    "value_text",
    "value_number",
    "value_boolean",
    "value_date",
    "value_datetime",
    "value_user_id",
    "value_json",
)


def _member(db: Session, environment_id: uuid.UUID, user_id: uuid.UUID | None) -> bool:
    if not user_id:
        return False
    user = db.get(User, user_id)
    return bool(
        user
        and user.is_active
        and user.status == "active"
        and db.scalar(
            select(EnvironmentMembership.id).where(
                EnvironmentMembership.environment_id == environment_id,
                EnvironmentMembership.user_id == user_id,
                EnvironmentMembership.is_active.is_(True),
            )
        )
    )


def _fields(db: Session, form_id: uuid.UUID | None) -> list[FieldDefinition]:
    return (
        []
        if not form_id
        else list(
            db.scalars(
                select(FieldDefinition)
                .where(FieldDefinition.form_definition_id == form_id, FieldDefinition.is_active.is_(True))
                .order_by(FieldDefinition.sort_order)
            )
        )
    )


def _value(row: CaseFieldValue | None) -> Any:
    if not row:
        return None
    for name in VALUE_COLUMNS:
        value = getattr(row, name)
        if value is not None:
            return (
                str(value)
                if name in {"value_date", "value_datetime", "value_user_id", "value_number"}
                else value
            )
    return None


def build_preview(db: Session, item: Case, target_environment_id: uuid.UUID) -> dict[str, Any]:
    target = db.get(Environment, target_environment_id)
    if not target or not target.is_active or target.id == item.environment_id:
        raise HTTPException(422, "יש לבחור סביבת יעד פעילה ושונה מהסביבה הנוכחית")
    request_types = list(
        db.scalars(
            select(RequestType)
            .where(RequestType.environment_id == target.id, RequestType.is_active.is_(True))
            .order_by(RequestType.sort_order)
        )
    )
    participants = list(db.scalars(select(CaseParticipant).where(CaseParticipant.case_id == item.id)))
    removed = [str(row.user_id) for row in participants if not _member(db, target.id, row.user_id)]
    fields = _fields(db, item.form_definition_id)
    values = {
        row.field_definition_id: row
        for row in db.scalars(select(CaseFieldValue).where(CaseFieldValue.case_id == item.id))
    }
    return {
        "case_id": str(item.id),
        "case_number": item.case_number,
        "from_environment_id": str(item.environment_id),
        "to_environment_id": str(target.id),
        "target_environment_name": target.name_he,
        "request_types": [
            {"id": str(row.id), "name_he": row.name_he, "requires_approval": row.requires_approval}
            for row in request_types
        ],
        "removed_participant_ids": removed,
        "assignee_will_be_removed": bool(item.assignee_id and not _member(db, target.id, item.assignee_id)),
        "current_fields": [
            {
                "field_id": str(field.id),
                "key": field.key,
                "label": field.label_he,
                "field_type": field.field_type,
                "value": _value(values.get(field.id)),
            }
            for field in fields
            if field.id in values
        ],
        "warning": "מידע היסטורי יישמר, אך שדות ומשתתפים שאינם תקפים בסביבה החדשה יוסרו מהקריאה הפעילה.",
    }


def target_requirements(db: Session, item: Case, request_type: RequestType) -> dict[str, Any]:
    _, initial = resolve_workflow(db, request_type)
    fields, old_fields = _fields(db, request_type.form_version_id), _fields(db, item.form_definition_id)
    priorities = list(
        db.scalars(
            select(PriorityDefinition)
            .where(
                PriorityDefinition.environment_id == request_type.environment_id,
                PriorityDefinition.is_active.is_(True),
            )
            .order_by(PriorityDefinition.sort_order)
        )
    )
    sub_priorities = list(
        db.scalars(
            select(SubPriorityDefinition)
            .where(
                SubPriorityDefinition.environment_id == request_type.environment_id,
                SubPriorityDefinition.is_active.is_(True),
            )
            .order_by(SubPriorityDefinition.sort_order)
        )
    )
    assignees = list(
        db.scalars(
            select(User)
            .join(EnvironmentMembership, EnvironmentMembership.user_id == User.id)
            .where(
                EnvironmentMembership.environment_id == request_type.environment_id,
                EnvironmentMembership.is_active.is_(True),
                User.is_active.is_(True),
                User.status == "active",
            )
            .order_by(User.display_name)
        ).unique()
    )
    old_by_key = {row.key: row for row in old_fields}
    mapped, required = [], []
    for field in fields:
        old = old_by_key.get(field.key)
        if old and old.field_type == field.field_type:
            mapped.append(
                {"from_field_id": str(old.id), "to_field_id": str(field.id), "label": field.label_he}
            )
        elif field.is_required:
            required.append({"id": str(field.id), "label": field.label_he, "field_type": field.field_type})
    mapped_old = {row["from_field_id"] for row in mapped}
    return {
        "initial_status_id": str(initial.id),
        "initial_status_label": initial.label_he,
        "target_fields": [
            {
                "id": str(row.id),
                "label": row.label_he,
                "field_type": row.field_type,
                "required": row.is_required,
            }
            for row in fields
        ],
        "field_mappings": mapped,
        "required_fields": required,
        "priorities": [{"id": str(row.id), "label_he": row.label_he} for row in priorities],
        "sub_priorities": [
            {
                "id": str(row.id),
                "priority_id": str(row.priority_id) if row.priority_id else None,
                "label_he": row.label_he,
            }
            for row in sub_priorities
        ],
        "assignees": [
            {"id": str(row.id), "display_name": row.display_name, "email": row.email} for row in assignees
        ],
        "removed_fields": [
            {"id": str(row.id), "label": row.label_he} for row in old_fields if str(row.id) not in mapped_old
        ],
    }


def transfer(db: Session, item: Case, actor: User, payload: Any) -> CaseTransferHistory:
    target_type = db.get(RequestType, payload.target_request_type_id)
    if (
        not target_type
        or not target_type.is_active
        or target_type.environment_id != payload.target_environment_id
    ):
        raise HTTPException(422, "סוג הקריאה אינו פעיל בסביבת היעד")
    priority = db.get(PriorityDefinition, payload.priority_id)
    if not priority or not priority.is_active or priority.environment_id != payload.target_environment_id:
        raise HTTPException(422, "יש לבחור עדיפות פעילה מסביבת היעד")
    if payload.sub_priority_id:
        sub = db.get(SubPriorityDefinition, payload.sub_priority_id)
        if (
            not sub
            or not sub.is_active
            or sub.environment_id != payload.target_environment_id
            or sub.priority_id != priority.id
        ):
            raise HTTPException(422, "תת-העדיפות אינה תואמת לסביבת היעד ולעדיפות")
    if payload.assignee_id and not _member(db, payload.target_environment_id, payload.assignee_id):
        raise HTTPException(422, "המטפל אינו פעיל או משויך לסביבת היעד")
    requirements = target_requirements(db, item, target_type)
    supplied = {str(row.field_definition_id): row.value for row in payload.new_field_values}
    missing = [
        row["label"] for row in requirements["required_fields"] if supplied.get(row["id"]) in (None, "", [])
    ]
    if missing:
        raise HTTPException(422, "חובה למלא: " + ", ".join(missing))
    old_env, old_type, old_status = item.environment_id, item.request_type_id, item.workflow_status_id
    old_sla = {
        "policy_id": str(item.sla_policy_id) if item.sla_policy_id else None,
        "response_due_at": item.response_due_at.isoformat() if item.response_due_at else None,
        "resolution_due_at": item.resolution_due_at.isoformat() if item.resolution_due_at else None,
    }
    current_values = {
        row.field_definition_id: row
        for row in db.scalars(select(CaseFieldValue).where(CaseFieldValue.case_id == item.id))
    }
    mappings = {
        uuid.UUID(row["to_field_id"]): uuid.UUID(row["from_field_id"])
        for row in requirements["field_mappings"]
    }
    removed_snapshot = [
        {"field_id": str(fid), "value": _value(value)}
        for fid, value in current_values.items()
        if fid not in set(mappings.values())
    ]
    participants = list(db.scalars(select(CaseParticipant).where(CaseParticipant.case_id == item.id)))
    removed_participants = [
        str(row.user_id)
        for row in participants
        if not _member(db, payload.target_environment_id, row.user_id)
    ]
    if removed_participants:
        db.execute(
            delete(CaseParticipant).where(
                CaseParticipant.case_id == item.id,
                CaseParticipant.user_id.in_([uuid.UUID(value) for value in removed_participants]),
            )
        )
    removed_assignee = (
        {"user_id": str(item.assignee_id)}
        if item.assignee_id and not _member(db, payload.target_environment_id, item.assignee_id)
        else None
    )
    pending = list(
        db.scalars(
            select(ApprovalInstance).where(
                ApprovalInstance.case_id == item.id, ApprovalInstance.status == "pending"
            )
        )
    )
    for approval in pending:
        approval.status = "cancelled"
        approval.cancelled_at = datetime.now(UTC)
        approval.completed_at = datetime.now(UTC)
        for task in db.scalars(
            select(ApprovalTask).where(
                ApprovalTask.approval_instance_id == approval.id, ApprovalTask.status == "pending"
            )
        ):
            task.status = "cancelled"
            task.comment = "environment_transfer"
    db.execute(delete(CaseFieldValue).where(CaseFieldValue.case_id == item.id))
    for target_id, source_id in mappings.items():
        source = current_values.get(source_id)
        if source:
            db.add(
                CaseFieldValue(
                    case_id=item.id,
                    field_definition_id=target_id,
                    **{name: getattr(source, name) for name in VALUE_COLUMNS},
                )
            )
    target_fields = {row.id: row for row in _fields(db, target_type.form_version_id)}
    from app.modules.api import typed_value

    for field_id, value in supplied.items():
        field = target_fields.get(uuid.UUID(field_id))
        if not field:
            raise HTTPException(422, "שדה היעד אינו שייך לטופס החדש")
        db.execute(
            delete(CaseFieldValue).where(
                CaseFieldValue.case_id == item.id, CaseFieldValue.field_definition_id == field.id
            )
        )
        db.add(typed_value(item.id, field, value))
    item.environment_id = payload.target_environment_id
    item.request_type_id = target_type.id
    item.form_definition_id = target_type.form_version_id
    item.priority_id = priority.id
    item.sub_priority_id = payload.sub_priority_id
    item.assignee_id = payload.assignee_id
    item.assigned_group_id = None
    item.sla_policy_id = None
    item.response_due_at = None
    item.resolution_due_at = None
    item.sla_response_status = "not_started"
    item.sla_resolution_status = "not_started"
    item.approval_status = "not_started"
    item.is_approved = False
    item.version += 1
    initial = initialize_operations(db, item, target_type)
    started = start_matching_approvals(db, item)
    AutomationEngine.run(
        db,
        item,
        "case_transferred",
        {
            "from_environment_id": str(old_env),
            "environment_id": str(item.environment_id),
            "request_type_id": str(item.request_type_id),
        },
    )
    history = CaseTransferHistory(
        case_id=item.id,
        from_environment_id=old_env,
        to_environment_id=item.environment_id,
        from_request_type_id=old_type,
        to_request_type_id=item.request_type_id,
        from_status_id=old_status,
        to_status_id=initial.id,
        transferred_by=actor.id,
        removed_participants=removed_participants,
        removed_assignee=removed_assignee,
        removed_fields_snapshot=removed_snapshot,
        new_values=[{"field_id": key} for key in supplied],
        approval_effect={"cancelled": len(pending), "created": len(started)},
        sla_effect={"old": old_sla, "new_policy_id": str(item.sla_policy_id) if item.sla_policy_id else None},
        reason=payload.reason,
    )
    db.add(history)
    return history
