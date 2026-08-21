import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.modules.approvals.service import start_matching_approvals
from app.modules.automation.service import AutomationEngine
from app.modules.case_semantics.service import CaseSemanticFieldService
from app.modules.global_case_values.service import active_values
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
    GlobalCaseFieldValue,
    GlobalPriorityDefinition,
    GlobalStatusDefinition,
    GlobalSubPriorityDefinition,
    RequestType,
    User,
)
from app.modules.operations.service import initialize_sla

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
    global_count = db.scalar(select(func.count()).select_from(GlobalCaseFieldValue).where(
        GlobalCaseFieldValue.case_id == item.id)) or 0
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
        "global_fields_preserved": global_count,
        "environment_fields_removed": len(values),
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
    fields, old_fields = _fields(db, request_type.form_version_id), _fields(db, item.form_definition_id)
    priorities = active_values(db, "priorities")
    sub_priorities = active_values(db, "sub-priorities")
    current_status = db.get(GlobalStatusDefinition, item.workflow_status_id)
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
    return {
        "initial_status_id": str(current_status.id) if current_status else None,
        "initial_status_label": current_status.label_he if current_status else "",
        "target_fields": [
            {
                "id": str(row.id),
                "label": row.label_he,
                "field_type": row.field_type,
                "required": row.is_required,
            }
            for row in fields
        ],
        "field_mappings": [],
        "required_fields": [],
        "priorities": [{"id": str(row.id), "label_he": row.label_he} for row in priorities],
        "sub_priorities": [
            {
                "id": str(row.id),
                "priority_id": None,
                "label_he": row.label_he,
            }
            for row in sub_priorities
        ],
        "assignees": [
            {"id": str(row.id), "display_name": row.display_name, "email": row.email} for row in assignees
        ],
        "removed_fields": [
            {"id": str(row.id), "label": row.label_he} for row in old_fields
        ],
        "global_fields_preserved": db.scalar(
            select(func.count()).select_from(GlobalCaseFieldValue).where(
                GlobalCaseFieldValue.case_id == item.id
            )
        ) or 0,
    }


def transfer(db: Session, item: Case, actor: User, payload: Any) -> CaseTransferHistory:
    target_type = db.get(RequestType, payload.target_request_type_id)
    if (
        not target_type
        or not target_type.is_active
        or target_type.environment_id != payload.target_environment_id
    ):
        raise HTTPException(422, "סוג הקריאה אינו פעיל בסביבת היעד")
    priority_id = payload.priority_id or item.priority_id
    priority = db.get(GlobalPriorityDefinition, priority_id) if priority_id else None
    if payload.priority_id and (not priority or not priority.is_active):
        raise HTTPException(422, "העדיפות הגלובלית שנבחרה אינה פעילה")
    if payload.sub_priority_id:
        sub = db.get(GlobalSubPriorityDefinition, payload.sub_priority_id)
        if not sub or not sub.is_active:
            raise HTTPException(422, "תת־העדיפות הגלובלית אינה פעילה")
    if payload.assignee_id and not _member(db, payload.target_environment_id, payload.assignee_id):
        raise HTTPException(422, "המטפל אינו פעיל או משויך לסביבת היעד")
    supplied = {str(row.field_definition_id): row.value for row in payload.new_field_values}
    semantics = CaseSemanticFieldService(db)
    conflicts = semantics.sync_case(item)
    if conflicts:
        raise HTTPException(409, "קיימת סתירה בערכים הסמנטיים של הקריאה; יש לפתור אותה לפני העברה")
    old_env, old_type = item.environment_id, item.request_type_id
    old_status = semantics.value_id(item, "case.status")
    old_sla = {
        "policy_id": str(item.sla_policy_id) if item.sla_policy_id else None,
        "response_due_at": item.response_due_at.isoformat() if item.response_due_at else None,
        "resolution_due_at": item.resolution_due_at.isoformat() if item.resolution_due_at else None,
    }
    current_values = {
        row.field_definition_id: row
        for row in db.scalars(select(CaseFieldValue).where(CaseFieldValue.case_id == item.id))
    }
    removed_snapshot = [
        {"field_id": str(fid), "value": _value(value)}
        for fid, value in current_values.items()
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
    if payload.priority_id:
        semantics.write(item, "case.priority", payload.priority_id)
    if payload.sub_priority_id is not None:
        semantics.write(item, "case.sub_priority", payload.sub_priority_id)
    effective_assignee = payload.assignee_id
    if effective_assignee is None and _member(db, payload.target_environment_id, item.assignee_id):
        effective_assignee = item.assignee_id
    semantics.write(item,"case.assignee",effective_assignee)
    preserved_semantics = {
        binding: semantics.value_id(item, binding)
        for binding in ("case.status", "case.priority", "case.sub_priority", "case.assignee")
    }
    item.assigned_group_id = None
    item.sla_policy_id = None
    item.response_due_at = None
    item.resolution_due_at = None
    item.sla_response_status = "not_started"
    item.sla_resolution_status = "not_started"
    item.approval_status = "not_started"
    item.is_approved = False
    item.version += 1
    initialize_sla(db,item)
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
    for binding, value_id in preserved_semantics.items():
        semantics.write(item, binding, value_id, require_active=False)
    history = CaseTransferHistory(
        case_id=item.id,
        from_environment_id=old_env,
        to_environment_id=item.environment_id,
        from_request_type_id=old_type,
        to_request_type_id=item.request_type_id,
        from_status_id=old_status,
        to_status_id=old_status,
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
