import io
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import delete, func, or_, select

from app.modules.access.mapping import codes
from app.modules.access.models import PermissionDomain
from app.modules.access.service import replace_levels
from app.modules.api import DB, Current, audit, case_access, permissions, require
from app.modules.approvals.service import create_step_tasks, resubmit_approval
from app.modules.case_visibility.service import CaseVisibilityService
from app.modules.models import (
    ApprovalFlowDefinition,
    ApprovalInstance,
    ApprovalStepDefinition,
    ApprovalTask,
    AutomationExecutionLog,
    Case,
    CaseFieldDefinition,
    Environment,
    EnvironmentGlobalCaseField,
    GlobalCaseFieldDefinition,
    GlobalPriorityDefinition,
    GlobalStatusDefinition,
    Permission,
    RequestType,
    User,
    UserPermissionAssignment,
)
from app.modules.numbering.service import NumberingService
from app.modules.operations.models import Notification

router = APIRouter(prefix="/api", tags=["configurable-platform"])
FIELD_TYPES = {"short_text", "long_text", "number", "date", "datetime", "boolean",
               "single_select", "multi_select", "user", "group", "email", "phone"}


class OptionIn(BaseModel):
    value: str
    label_he: str
    label_en: str = ""
    is_active: bool = True
    sort_order: int = 0


class OptionReorderIn(BaseModel):
    ids: list[str] = Field(min_length=1)


class CaseFieldIn(BaseModel):
    request_type_id: uuid.UUID | None = None
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    label_he: str = Field(min_length=1)
    label_en: str = ""
    description: str | None = None
    field_type: str
    is_required: bool = False
    is_active: bool = True
    options_json: list[OptionIn] = Field(default_factory=list)
    default_value_json: Any = None
    validation_json: dict[str, Any] = Field(default_factory=dict)
    sort_order: int = 0

    @model_validator(mode="after")
    def validate_configuration(self) -> "CaseFieldIn":
        if self.field_type not in FIELD_TYPES:
            raise ValueError("סוג השדה אינו נתמך")
        if self.field_type == "single_select" and not self.options_json:
            raise ValueError("יש להזין לפחות אפשרות אחת")
        if self.field_type == "multi_select" and len(self.options_json) < 2:
            raise ValueError("יש להזין לפחות שתי אפשרויות")
        if self.field_type not in {"single_select", "multi_select"}:
            self.options_json = []
        return self


def case_field_dict(row: CaseFieldDefinition) -> dict[str, Any]:
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


@router.get("/environments/{environment_id}/case-fields")
def list_case_fields(environment_id: uuid.UUID, db: DB, user: Current,
                     request_type_id: uuid.UUID | None = None,
                     presentation: str | None = None) -> dict[str, list[dict[str, Any]]]:
    require(db, user, environment_id, "environment.read")
    query = select(CaseFieldDefinition).where(CaseFieldDefinition.environment_id == environment_id)
    if request_type_id:
        query = query.where(or_(CaseFieldDefinition.request_type_id.is_(None),
                                CaseFieldDefinition.request_type_id == request_type_id))
    environment_fields = [case_field_dict(row) for row in db.scalars(query.order_by(CaseFieldDefinition.sort_order))]
    configurations = {row.global_field_id: row for row in db.scalars(select(EnvironmentGlobalCaseField).where(
        EnvironmentGlobalCaseField.environment_id == environment_id))}
    global_fields = []
    for row in db.scalars(select(GlobalCaseFieldDefinition).order_by(GlobalCaseFieldDefinition.sort_order)):
        config = configurations.get(row.id)
        visible = (config.is_visible if config else True)
        if presentation == "create": visible = visible and (config.show_on_create if config else True)
        if presentation == "edit": visible = visible and (config.show_on_edit if config else True)
        if row.is_active and visible:
            global_fields.append({"id": row.id, "key": row.key, "label_he": row.label_he,
                "label_en": row.label_en, "field_type": row.field_type,
                "is_required": config.is_required if config else False,
                "is_active": row.is_active, "sort_order": row.sort_order,
                "configuration_json": row.configuration_json or {}, "source": "global",
                "semantic_binding": row.semantic_binding,
                "environment_configuration": {
                    "is_visible": config.is_visible if config else True,
                    "is_required": config.is_required if config else False,
                    "show_on_create": config.show_on_create if config else True,
                    "show_on_edit": config.show_on_edit if config else True,
                }})
    return {"global_fields": global_fields, "environment_fields": environment_fields}


@router.post("/environments/{environment_id}/case-fields", status_code=201)
def create_case_field(environment_id: uuid.UUID, data: CaseFieldIn, db: DB,
                      user: Current) -> dict[str, Any]:
    require(db, user, environment_id, "environment.fields.manage")
    if data.request_type_id:
        request_type = db.get(RequestType, data.request_type_id)
        if not request_type or request_type.environment_id != environment_id:
            raise HTTPException(422, "סוג הקריאה אינו שייך לסביבה")
    payload = data.model_dump()
    payload["options_json"] = [row.model_dump() for row in data.options_json]
    item = CaseFieldDefinition(id=uuid.uuid4(), system_number=NumberingService.next(db, "case_field", environment_id),
                               environment_id=environment_id, created_by=user.id, **payload)
    db.add(item); db.flush(); audit(db, user, "case_field", item.id, "created"); db.commit()
    return case_field_dict(item)


@router.patch("/environments/{environment_id}/case-fields/{field_id}")
def update_case_field(environment_id: uuid.UUID, field_id: uuid.UUID, data: CaseFieldIn,
                      db: DB, user: Current) -> dict[str, Any]:
    require(db, user, environment_id, "environment.fields.manage")
    item = db.get(CaseFieldDefinition, field_id)
    if not item or item.environment_id != environment_id:
        raise HTTPException(404, "שדה הקריאה לא נמצא")
    payload = data.model_dump(); payload["options_json"] = [row.model_dump() for row in data.options_json]
    for key, value in payload.items(): setattr(item, key, value)
    audit(db, user, "case_field", item.id, "updated"); db.commit(); return case_field_dict(item)


@router.put("/environments/{environment_id}/case-fields/{field_id}/options/reorder")
def reorder_case_field_options(environment_id: uuid.UUID, field_id: uuid.UUID,
                               data: OptionReorderIn, db: DB, user: Current) -> dict[str, Any]:
    require(db, user, environment_id, "environment.fields.manage")
    item = db.get(CaseFieldDefinition, field_id)
    if not item or item.environment_id != environment_id:
        raise HTTPException(404, "שדה הקריאה לא נמצא")
    if item.field_type not in {"single_select", "multi_select"}:
        raise HTTPException(422, "רק שדה בחירה תומך בסידור אפשרויות")
    options = list(item.options_json or [])
    by_id = {str(option.get("value")): option for option in options}
    if len(data.ids) != len(set(data.ids)) or set(data.ids) != set(by_id):
        raise HTTPException(422, "רשימת הסידור אינה תואמת לאפשרויות השדה")
    item.options_json = [{**by_id[value], "sort_order": index} for index, value in enumerate(data.ids)]
    audit(db, user, "case_field", item.id, "options_reordered", after={"ids": data.ids})
    db.commit()
    return case_field_dict(item)


class PermissionAssignmentIn(BaseModel):
    permission_code: str
    environment_id: uuid.UUID | None = None
    is_allowed: bool = True


@router.get("/permissions/catalog")
def permission_catalog(db: DB, user: Current) -> list[dict[str, Any]]:
    return [{column.name: getattr(row, column.name) for column in row.__table__.columns}
            for row in db.scalars(select(Permission).order_by(Permission.category, Permission.code))]


@router.get("/users/{user_id}/direct-permissions")
def user_direct_permissions(user_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    if not user.is_system_admin: raise HTTPException(403, "נדרש מנהל מערכת")
    return [{"id": row.id, "permission_code": row.permission_code,
             "environment_id": row.environment_id, "is_allowed": row.is_allowed}
            for row in db.scalars(select(UserPermissionAssignment).where(UserPermissionAssignment.user_id == user_id))]


@router.post("/users/{user_id}/direct-permissions", status_code=201)
def assign_user_permission(user_id: uuid.UUID, data: PermissionAssignmentIn, db: DB,
                           user: Current) -> dict[str, Any]:
    if not user.is_system_admin: raise HTTPException(403, "נדרש מנהל מערכת")
    if not db.get(Permission, data.permission_code): raise HTTPException(404, "ההרשאה לא נמצאה")
    item = UserPermissionAssignment(user_id=user_id, created_by=user.id, **data.model_dump())
    db.add(item)
    levels: dict[str, str] = {}
    for domain in db.scalars(select(PermissionDomain).where(PermissionDomain.is_active.is_(True))):
        if data.permission_code in codes(domain.edit_permissions):
            levels[domain.code] = "edit" if data.is_allowed else "none"
        elif data.permission_code in codes(domain.view_permissions):
            levels[domain.code] = "view" if data.is_allowed else "none"
    replace_levels(db, user.id, "users", [user_id], data.environment_id, levels)
    db.commit(); return {"id": item.id}


@router.delete("/users/{user_id}/direct-permissions/{assignment_id}", status_code=204)
def remove_user_permission(user_id: uuid.UUID, assignment_id: uuid.UUID, db: DB, user: Current) -> None:
    if not user.is_system_admin: raise HTTPException(403, "נדרש מנהל מערכת")
    item = db.get(UserPermissionAssignment, assignment_id)
    if not item or item.user_id != user_id: raise HTTPException(404, "השיוך לא נמצא")
    levels = {domain.code: "inherit" for domain in db.scalars(
        select(PermissionDomain).where(PermissionDomain.is_active.is_(True)))
        if item.permission_code in codes(domain.view_permissions) | codes(domain.edit_permissions)}
    replace_levels(db, user.id, "users", [user_id], item.environment_id, levels)
    db.delete(item); db.commit()


@router.get("/users/{user_id}/effective-permissions")
def effective_permissions(user_id: uuid.UUID, environment_id: uuid.UUID, db: DB,
                          user: Current) -> dict[str, Any]:
    if not user.is_system_admin and user.id != user_id: raise HTTPException(403, "אין הרשאה")
    target = db.get(User, user_id)
    if not target: raise HTTPException(404, "המשתמש לא נמצא")
    return {"permissions": sorted(permissions(db, target, environment_id)),
            "policy": "explicit_deny_overrides_allow; system_administrator_overrides_all"}


class ApprovalStepIn(BaseModel):
    name: str
    approver_type: str = "user"
    approver_user_id: uuid.UUID | None = None
    approver_group_id: uuid.UUID | None = None
    approver_field_key: str | None = None
    approver_environment_role: str | None = None
    approver_job_title: str | None = None
    approver_user_field_id: uuid.UUID | None = None
    approver_case_field_id: uuid.UUID | None = None
    required_approvals: int = 1
    approval_mode: str = Field("any", pattern="^(any|all|minimum_count)$")
    description: str | None = None
    is_active: bool = True
    allow_reject: bool = True
    allow_return: bool = True
    timeout_hours: int | None = None


class ApprovalFlowIn(BaseModel):
    name: str
    description: str | None = None
    request_type_id: uuid.UUID | None = None
    trigger_type: str = "case_created"
    is_active: bool = True
    approval_policy: str = Field("all_active_steps", pattern="^(all_active_steps|highest_active_step)$")
    steps: list[ApprovalStepIn] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def validate_simple_stages(self) -> "ApprovalFlowIn":
        for step in self.steps:
            if step.approver_type == "user" and step.approver_user_id: continue
            if step.approver_type == "job_title" and step.approver_job_title:
                step.approval_mode = "any"; step.required_approvals = 1; continue
            raise ValueError("כל שלב אישור חייב לבחור משתמש או תפקיד ארגוני")
        if any(not step.is_active for step in self.steps[:-1]) and self.steps[-1].is_active:
            raise ValueError("שלבים פעילים חייבים להיות רציפים")
        return self


def flow_dict(db: DB, row: ApprovalFlowDefinition) -> dict[str, Any]:
    steps = db.scalars(select(ApprovalStepDefinition).where(
        ApprovalStepDefinition.approval_flow_id == row.id).order_by(ApprovalStepDefinition.step_order)).all()
    return {"id": row.id, "system_number": row.system_number, "name": row.name,
            "description": row.description, "request_type_id": row.request_type_id,
            "trigger_type": row.trigger_type, "is_active": row.is_active,
            "approval_policy": row.approval_policy,
            "steps": [{column.name: getattr(step, column.name) for column in step.__table__.columns} for step in steps]}


@router.get("/environments/{environment_id}/approval-flows")
def list_flows(environment_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    require(db, user, environment_id, "environment.read")
    return [flow_dict(db, row) for row in db.scalars(select(ApprovalFlowDefinition).where(
        ApprovalFlowDefinition.environment_id == environment_id))]


@router.post("/environments/{environment_id}/approval-flows", status_code=201)
def create_flow(environment_id: uuid.UUID, data: ApprovalFlowIn, db: DB,
                user: Current) -> dict[str, Any]:
    require(db, user, environment_id, "environment.manage")
    item = ApprovalFlowDefinition(id=uuid.uuid4(), system_number=NumberingService.next(db, "approval_flow", environment_id),
                                  environment_id=environment_id, created_by=user.id,
                                  **data.model_dump(exclude={"steps"}))
    db.add(item); db.flush()
    for index, step in enumerate(data.steps, 1):
        db.add(ApprovalStepDefinition(id=uuid.uuid4(), approval_flow_id=item.id,
                                      step_order=index, **step.model_dump()))
    audit(db, user, "approval_flow", item.id, "created"); db.commit(); return flow_dict(db, item)


@router.put("/approval-flows/{flow_id}")
def update_flow(flow_id: uuid.UUID, data: ApprovalFlowIn, db: DB, user: Current) -> dict[str, Any]:
    item = db.get(ApprovalFlowDefinition, flow_id)
    if not item: raise HTTPException(404, "סבב האישורים לא נמצא")
    require(db, user, item.environment_id, "environment.manage")
    before = jsonable_encoder(flow_dict(db, item))
    if db.scalar(select(ApprovalInstance.id).where(ApprovalInstance.approval_flow_id == item.id).limit(1)):
        item.is_active = False
        replacement = ApprovalFlowDefinition(
            id=uuid.uuid4(), system_number=NumberingService.next(db, "approval_flow", item.environment_id),
            environment_id=item.environment_id, created_by=user.id,
            **data.model_dump(exclude={"steps"}),
        )
        db.add(replacement); db.flush()
        for index, step in enumerate(data.steps, 1):
            db.add(ApprovalStepDefinition(id=uuid.uuid4(), approval_flow_id=replacement.id,
                                          step_order=index, **step.model_dump()))
        audit(db, user, "approval_flow", replacement.id, "version_created", before=before,
              after=data.model_dump(mode="json"))
        db.commit()
        return flow_dict(db, replacement)
    for key, value in data.model_dump(exclude={"steps"}).items(): setattr(item, key, value)
    db.execute(delete(ApprovalStepDefinition).where(ApprovalStepDefinition.approval_flow_id == item.id))
    for index, step in enumerate(data.steps, 1):
        db.add(ApprovalStepDefinition(id=uuid.uuid4(), approval_flow_id=item.id,
                                      step_order=index, **step.model_dump()))
    audit(db, user, "approval_flow", item.id, "updated", before=before,
          after=data.model_dump(mode="json"))
    db.commit(); return flow_dict(db, item)


class ApprovalDecisionIn(BaseModel):
    decision: str = Field(pattern="^(approved|rejected|returned)$")
    comment: str | None = None


@router.get("/cases/{case_id}/approvals")
def case_approvals(case_id: uuid.UUID, db: DB, user: Current) -> dict[str, Any]:
    item = db.get(Case, case_id)
    if not item: raise HTTPException(404, "הקריאה לא נמצאה")
    case_access(db, user, item)
    rows = db.execute(select(ApprovalInstance, ApprovalFlowDefinition).join(
        ApprovalFlowDefinition, ApprovalInstance.approval_flow_id == ApprovalFlowDefinition.id).where(
        ApprovalInstance.case_id == case_id).order_by(
            ApprovalInstance.attempt_number.desc(),
            func.coalesce(ApprovalInstance.completed_at, ApprovalInstance.started_at).desc())).all()
    result = []
    for instance, flow in rows:
        tasks = []
        for task, step in db.execute(select(ApprovalTask, ApprovalStepDefinition).join(
            ApprovalStepDefinition, ApprovalTask.step_definition_id == ApprovalStepDefinition.id).where(
            ApprovalTask.approval_instance_id == instance.id).order_by(ApprovalStepDefinition.step_order)):
            tasks.append({"id": task.id, "step_order": step.step_order, "step_name": step.name,
                "approver_type": step.approver_type, "approver_user_id": task.approver_user_id,
                "approver_name": task.approver_name_snapshot, "status": task.status,
                "decision": task.decision, "comment": task.comment, "requested_at": instance.started_at,
                "decided_at": task.decided_at, "can_decide": task.approver_user_id == user.id
                    and task.status == "pending" and step.step_order == instance.current_step_order})
        result.append({"id": instance.id, "system_number": instance.system_number, "name": flow.name,
            "attempt_number": instance.attempt_number, "status": instance.status,
            "current_step_order": instance.current_step_order, "started_at": instance.started_at,
            "completed_at": instance.completed_at, "tasks": tasks})
    current = result[0] if result else None
    can_resubmit = bool(current and current["status"] in {"rejected", "returned"} and (
        user.is_system_admin or "case.update" in permissions(db, user, item.environment_id)))
    return {"current_approval": current, "approval_history": result[1:],
            "can_resubmit": can_resubmit}


@router.post("/cases/{case_id}/approvals/resubmit")
def resubmit_case_approval(case_id: uuid.UUID, db: DB, user: Current) -> dict[str, Any]:
    item = db.get(Case, case_id)
    if not item: raise HTTPException(404, "הקריאה לא נמצאה")
    case_access(db, user, item)
    require(db, user, item.environment_id, "case.update")
    instance = resubmit_approval(db, item)
    audit(db, user, "approval_instance", instance.id, "resubmitted",
          after={"attempt_number": instance.attempt_number})
    db.commit()
    return {"id": instance.id, "attempt_number": instance.attempt_number, "status": instance.status}


@router.get("/approvals/pending-for-me")
def pending_approvals_for_me(db: DB, user: Current) -> list[dict[str, Any]]:
    rows = db.execute(
        select(ApprovalTask, ApprovalInstance, ApprovalStepDefinition, Case, Environment, RequestType)
        .join(ApprovalInstance, ApprovalTask.approval_instance_id == ApprovalInstance.id)
        .join(ApprovalStepDefinition, ApprovalTask.step_definition_id == ApprovalStepDefinition.id)
        .join(Case, ApprovalInstance.case_id == Case.id)
        .join(Environment, Case.environment_id == Environment.id)
        .join(RequestType, Case.request_type_id == RequestType.id)
        .where(
            ApprovalTask.approver_user_id == user.id,
            ApprovalTask.status == "pending",
            ApprovalInstance.status == "pending",
            ApprovalStepDefinition.step_order == ApprovalInstance.current_step_order,
        )
        .order_by(ApprovalInstance.started_at)
    ).all()
    return [{
        "task_id": task.id, "case_id": case_item.id, "case_number": case_item.case_number,
        "title": case_item.title, "description": case_item.description or "", "environment": environment.name_he,
        "request_type": request_type.name_he, "step_name": step.name,
        "requested_at": instance.started_at, "status": task.status,
    } for task, instance, step, case_item, environment, request_type in rows]


@router.post("/approval-tasks/{task_id}/decision")
def decide(task_id: uuid.UUID, data: ApprovalDecisionIn, db: DB, user: Current) -> dict[str, Any]:
    task = db.get(ApprovalTask, task_id)
    if not task or task.approver_user_id != user.id: raise HTTPException(403, "רק המאשר שנבחר רשאי להחליט")
    if task.status != "pending": raise HTTPException(409, "המשימה כבר הושלמה")
    instance = db.get(ApprovalInstance, task.approval_instance_id)
    if not instance: raise HTTPException(409, "תהליך האישור אינו זמין")
    if instance.status != "pending": raise HTTPException(409, "סבב האישורים אינו פעיל")
    if data.decision in {"rejected", "returned"} and not data.comment:
        raise HTTPException(422, "חובה להזין הערה עבור דחייה או החזרה")
    active_step_id = db.scalar(select(ApprovalStepDefinition.id).where(
        ApprovalStepDefinition.approval_flow_id == instance.approval_flow_id,
        ApprovalStepDefinition.step_order == instance.current_step_order))
    if task.step_definition_id != active_step_id:
        raise HTTPException(409, "משימת האישור אינה שייכת לשלב הפעיל")
    case_item = db.get(Case, instance.case_id)
    if not case_item: raise HTTPException(409, "הקריאה אינה זמינה")
    task.status = data.decision; task.decision = data.decision; task.comment = data.comment; task.decided_at = datetime.now(UTC)
    step_definition = db.get(ApprovalStepDefinition, task.step_definition_id)
    if step_definition and step_definition.approver_type == "job_title":
        for other in db.scalars(select(ApprovalTask).where(
            ApprovalTask.approval_instance_id == instance.id,
            ApprovalTask.step_definition_id == task.step_definition_id,
            ApprovalTask.id != task.id, ApprovalTask.status == "pending")):
            other.status = "cancelled"
    if data.decision in {"rejected", "returned"}:
        instance.status = data.decision; instance.completed_at = datetime.now(UTC)
        case_item.approval_status = data.decision; case_item.is_approved = False
        db.add(Notification(user_id=case_item.requester_id, notification_type=f"approval_{data.decision}",
                            title_he="התקבלה החלטה בסבב האישורים",
                            body_he=f"הקריאה {case_item.case_number} {('נדחתה' if data.decision == 'rejected' else 'הוחזרה לתיקון')}",
                            entity_type="case", entity_id=str(case_item.id)))
    else:
        step = db.get(ApprovalStepDefinition, task.step_definition_id)
        if not step: raise HTTPException(409, "שלב האישור אינו זמין")
        approved = db.scalar(select(func.count()).select_from(ApprovalTask).where(
            ApprovalTask.approval_instance_id == instance.id,
            ApprovalTask.step_definition_id == task.step_definition_id,
            ApprovalTask.status == "approved")) or 0
        total_tasks = db.scalar(select(func.count()).select_from(ApprovalTask).where(
            ApprovalTask.approval_instance_id == instance.id,
            ApprovalTask.step_definition_id == task.step_definition_id)) or 0
        required = total_tasks if step.approval_mode == "all" else 1 if step.approval_mode == "any" else step.required_approvals
        if approved >= required:
            next_step = db.scalar(select(ApprovalStepDefinition).where(
                ApprovalStepDefinition.approval_flow_id == instance.approval_flow_id,
                ApprovalStepDefinition.step_order > step.step_order).order_by(
                ApprovalStepDefinition.step_order).limit(1))
            if next_step:
                instance.current_step_order = next_step.step_order
                create_step_tasks(db, instance, next_step.step_order)
            else:
                instance.status = "approved"; instance.completed_at = datetime.now(UTC)
                case_item.approval_status = "approved"; case_item.is_approved = True
                case_item.approved_at = datetime.now(UTC)
                case_item.approved_by_summary = f"{instance.system_number}: {approved} מאשרים"
                db.add(Notification(user_id=case_item.requester_id, notification_type="approval_completed",
                                    title_he="הקריאה אושרה",
                                    body_he=f"סבב האישורים עבור {case_item.case_number} הושלם בהצלחה",
                                    entity_type="case", entity_id=str(case_item.id)))
    audit(db, user, "approval_instance", instance.id, data.decision); db.commit()
    return {"status": instance.status}


@router.get("/automation-executions")
def automation_logs(environment_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    require(db, user, environment_id, "environment.rules.manage")
    rows = db.execute(select(AutomationExecutionLog).join(Case).where(
        Case.environment_id == environment_id).order_by(AutomationExecutionLog.executed_at.desc())).scalars()
    return [{column.name: getattr(row, column.name) for column in row.__table__.columns} for row in rows]


def report_query(db: DB, user: Current, environment_id: uuid.UUID | None, request_type_id: uuid.UUID | None,
                 status: str | None, search: str | None, sort: str, direction: str,
                 created_by_id: uuid.UUID | None = None, assignee_id: uuid.UUID | None = None,
                 created_from: datetime | None = None, created_to: datetime | None = None,
                 updated_from: datetime | None = None, updated_to: datetime | None = None,
                 case_number: str | None = None, title: str | None = None,
                 description: str | None = None, priority: str | None = None,
                 workflow_status_id: uuid.UUID | None = None,
                 priority_id: uuid.UUID | None = None,
                 include_participating: bool = False) -> Any:
    query = select(Case, Environment, RequestType, User).join(Environment, Case.environment_id == Environment.id).join(
        RequestType, Case.request_type_id == RequestType.id).join(User, Case.requester_id == User.id)
    query = CaseVisibilityService(db, user).apply(query)
    if environment_id: query = query.where(Case.environment_id == environment_id)
    if request_type_id: query = query.where(Case.request_type_id == request_type_id)
    status_label = select(GlobalStatusDefinition.label_he).where(
        GlobalStatusDefinition.id == Case.workflow_status_id).correlate(Case).scalar_subquery()
    priority_label = select(GlobalPriorityDefinition.label_he).where(
        GlobalPriorityDefinition.id == Case.priority_id).correlate(Case).scalar_subquery()
    assignee_label = select(User.display_name).where(
        User.id == Case.assignee_id).correlate(Case).scalar_subquery()
    if status: query = query.where(status_label == status)
    if search: query = query.where(or_(Case.case_number.ilike(f"%{search}%"), Case.title.ilike(f"%{search}%")))
    if created_by_id: query = query.where(Case.reporter_id == created_by_id)
    if assignee_id: query = query.where(Case.assignee_id == assignee_id)
    if created_from: query = query.where(Case.created_at >= created_from)
    if created_to: query = query.where(Case.created_at <= created_to)
    if updated_from: query = query.where(Case.updated_at >= updated_from)
    if updated_to: query = query.where(Case.updated_at <= updated_to)
    if case_number: query = query.where(Case.case_number.ilike(f"%{case_number}%"))
    if title: query = query.where(Case.title.ilike(f"%{title}%"))
    if description: query = query.where(Case.description.ilike(f"%{description}%"))
    if priority: query = query.where(Case.priority == priority)
    if workflow_status_id: query = query.where(Case.workflow_status_id == workflow_status_id)
    if priority_id: query = query.where(Case.priority_id == priority_id)
    columns = {"case_number": Case.case_number, "created_at": Case.created_at,
               "updated_at": Case.updated_at, "priority": priority_label, "status": status_label,
               "title": Case.title, "environment": Environment.name_he,
               "request_type": RequestType.name_he, "requester": User.display_name,
               "assignee": assignee_label}
    column = columns.get(sort, Case.created_at)
    return query.order_by(column.asc() if direction == "asc" else column.desc())


def report_row(row: Any) -> dict[str, Any]:
    item, env, request_type, requester = row[:4]
    assignee = row[4] if len(row) > 4 else None
    status_label = row[5] if len(row) > 5 else item.status.value
    priority_label = row[6] if len(row) > 6 else item.priority
    return {"case_number": item.case_number, "environment": env.name_he,
            "request_type": request_type.name_he, "title": item.title,
            "description": item.description or "", "status": status_label or item.status.value,
            "priority": priority_label or "לא הוגדרה", "requester": requester.display_name,
            "assignee": assignee or "ללא מטפל",
            "created_at": item.created_at.isoformat(), "updated_at": item.updated_at.isoformat()}


def require_report_access(db: DB, user: Current, environment_id: uuid.UUID | None) -> None:
    if user.is_system_admin:
        return
    if environment_id:
        require(db, user, environment_id, "report.cases")
        return
    if not any("report.cases" in permissions(db, user, row.id) for row in db.scalars(select(Environment))):
        raise HTTPException(403, "אין הרשאה לצפות בדוח קריאות")


@router.get("/reports/cases")
def cases_report(db: DB, user: Current, environment_id: uuid.UUID | None = None,
                 request_type_id: uuid.UUID | None = None, status: str | None = None,
                 search: str | None = None, sort: str = "created_at", direction: str = "desc",
                 created_by_id: uuid.UUID | None = None, assignee_id: uuid.UUID | None = None,
                 created_from: datetime | None = None, created_to: datetime | None = None,
                 updated_from: datetime | None = None, updated_to: datetime | None = None,
                 case_number: str | None = None, title: str | None = None,
                 description: str | None = None, priority: str | None = None,
                 workflow_status_id: uuid.UUID | None = None, priority_id: uuid.UUID | None = None,
                 include_participating: bool = False,
                 page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200)) -> dict[str, Any]:
    require_report_access(db, user, environment_id)
    query = report_query(db, user, environment_id, request_type_id, status, search, sort, direction,
                         created_by_id, assignee_id, created_from, created_to, updated_from, updated_to,
                         case_number, title, description, priority, workflow_status_id, priority_id,
                         include_participating)
    query = query.add_columns(select(User.display_name).where(User.id == Case.assignee_id).correlate(Case).scalar_subquery().label("assignee"))
    query = query.add_columns(select(GlobalStatusDefinition.label_he).where(GlobalStatusDefinition.id == Case.workflow_status_id).correlate(Case).scalar_subquery().label("workflow_status"))
    query = query.add_columns(select(GlobalPriorityDefinition.label_he).where(GlobalPriorityDefinition.id == Case.priority_id).correlate(Case).scalar_subquery().label("priority_label"))
    rows = db.execute(query.offset((page - 1) * page_size).limit(page_size)).all()
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    return {"items": [report_row(row) for row in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/reports/cases/value-sources")
def report_value_sources(db: DB, user: Current, environment_id: uuid.UUID | None = None) -> dict[str, Any]:
    require_report_access(db, user, environment_id)
    status_query = select(GlobalStatusDefinition).where(GlobalStatusDefinition.is_active.is_(True))
    priority_query = select(GlobalPriorityDefinition).where(GlobalPriorityDefinition.is_active.is_(True))
    statuses = [{"id": row.id, "code": row.code, "label_he": row.label_he} for row in db.scalars(status_query.order_by(GlobalStatusDefinition.sort_order))]
    priorities = [{"id": row.id, "code": row.code, "label_he": row.label_he} for row in db.scalars(priority_query.order_by(GlobalPriorityDefinition.sort_order))]
    return {"statuses": statuses, "priorities": priorities}


def xlsx_bytes(rows: list[dict[str, Any]], filters: dict[str, str]) -> bytes:
    headers = ["מספר קריאה", "סביבה", "סוג קריאה", "נושא", "תיאור", "סטטוס", "עדיפות", "פותח", "מטפל", "נוצר", "עודכן"]
    keys = ["case_number", "environment", "request_type", "title", "description", "status", "priority", "requester", "assignee", "created_at", "updated_at"]
    book = Workbook()
    report_sheet = book.active
    report_sheet.title = "קריאות"
    report_sheet.append(headers)
    for row in rows:
        report_sheet.append([row[key] for key in keys])
    filter_sheet = book.create_sheet("מסננים")
    filter_sheet.append(["שם הדוח", "דוח קריאות שירות"])
    filter_sheet.append(["תאריך יצוא", datetime.now(UTC).isoformat()])
    for key, value in filters.items():
        filter_sheet.append([key, value])
    stream = io.BytesIO()
    book.save(stream)
    return stream.getvalue()


@router.get("/reports/cases/export")
def export_cases(db: DB, user: Current, environment_id: uuid.UUID | None = None,
                 request_type_id: uuid.UUID | None = None, status: str | None = None,
                 search: str | None = None, sort: str = "created_at", direction: str = "desc",
                 created_by_id: uuid.UUID | None = None, assignee_id: uuid.UUID | None = None,
                 created_from: datetime | None = None, created_to: datetime | None = None,
                 updated_from: datetime | None = None, updated_to: datetime | None = None,
                 case_number: str | None = None, title: str | None = None,
                 description: str | None = None, priority: str | None = None,
                 workflow_status_id: uuid.UUID | None = None, priority_id: uuid.UUID | None = None,
                 include_participating: bool = False) -> Response:
    require_report_access(db, user, environment_id)
    query = report_query(db, user, environment_id, request_type_id, status, search, sort, direction,
                         created_by_id, assignee_id, created_from, created_to, updated_from, updated_to,
                         case_number, title, description, priority, workflow_status_id, priority_id,
                         include_participating=include_participating)
    query = query.add_columns(select(User.display_name).where(User.id == Case.assignee_id).correlate(Case).scalar_subquery().label("assignee"))
    query = query.add_columns(select(GlobalStatusDefinition.label_he).where(GlobalStatusDefinition.id == Case.workflow_status_id).correlate(Case).scalar_subquery().label("workflow_status"))
    query = query.add_columns(select(GlobalPriorityDefinition.label_he).where(GlobalPriorityDefinition.id == Case.priority_id).correlate(Case).scalar_subquery().label("priority_label"))
    rows = [report_row(row) for row in db.execute(query.limit(5000)).all()]
    content = xlsx_bytes(rows, {"environment_id": str(environment_id or ""), "request_type_id": str(request_type_id or ""), "status": status or "", "search": search or "", "sort": sort, "direction": direction})
    return StreamingResponse(io.BytesIO(content), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="case-report.xlsx"'})
