import io
import uuid
import zipfile
from datetime import UTC, datetime
from html import escape
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, or_, select

from app.modules.api import DB, Current, audit, case_access, permissions, require
from app.modules.approvals.service import create_step_tasks
from app.modules.models import (
    ApprovalFlowDefinition,
    ApprovalInstance,
    ApprovalStepDefinition,
    ApprovalTask,
    AutomationExecutionLog,
    Case,
    CaseFieldDefinition,
    CaseParticipant,
    Environment,
    Permission,
    RequestType,
    User,
    UserPermissionAssignment,
)
from app.modules.numbering.service import NumberingService

router = APIRouter(prefix="/api", tags=["configurable-platform"])
FIELD_TYPES = {"short_text", "long_text", "number", "date", "datetime", "boolean",
               "single_select", "multi_select", "user", "group", "email", "phone"}


class OptionIn(BaseModel):
    value: str
    label_he: str
    label_en: str = ""
    is_active: bool = True
    sort_order: int = 0


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
                     request_type_id: uuid.UUID | None = None) -> list[dict[str, Any]]:
    require(db, user, environment_id, "environment.read")
    query = select(CaseFieldDefinition).where(CaseFieldDefinition.environment_id == environment_id)
    if request_type_id:
        query = query.where(or_(CaseFieldDefinition.request_type_id.is_(None),
                                CaseFieldDefinition.request_type_id == request_type_id))
    return [case_field_dict(row) for row in db.scalars(query.order_by(CaseFieldDefinition.sort_order))]


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
    db.add(item); db.commit(); return {"id": item.id}


@router.delete("/users/{user_id}/direct-permissions/{assignment_id}", status_code=204)
def remove_user_permission(user_id: uuid.UUID, assignment_id: uuid.UUID, db: DB, user: Current) -> None:
    if not user.is_system_admin: raise HTTPException(403, "נדרש מנהל מערכת")
    item = db.get(UserPermissionAssignment, assignment_id)
    if not item or item.user_id != user_id: raise HTTPException(404, "השיוך לא נמצא")
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
    required_approvals: int = 1
    allow_reject: bool = True
    allow_return: bool = True
    timeout_hours: int | None = None


class ApprovalFlowIn(BaseModel):
    name: str
    description: str | None = None
    request_type_id: uuid.UUID | None = None
    trigger_type: str = "case_created"
    is_active: bool = True
    steps: list[ApprovalStepIn] = Field(min_length=1)


def flow_dict(db: DB, row: ApprovalFlowDefinition) -> dict[str, Any]:
    steps = db.scalars(select(ApprovalStepDefinition).where(
        ApprovalStepDefinition.approval_flow_id == row.id).order_by(ApprovalStepDefinition.step_order)).all()
    return {"id": row.id, "system_number": row.system_number, "name": row.name,
            "description": row.description, "request_type_id": row.request_type_id,
            "trigger_type": row.trigger_type, "is_active": row.is_active,
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


class ApprovalDecisionIn(BaseModel):
    decision: str = Field(pattern="^(approved|rejected|returned)$")
    comment: str | None = None


@router.get("/cases/{case_id}/approvals")
def case_approvals(case_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    item = db.get(Case, case_id)
    if not item: raise HTTPException(404, "הקריאה לא נמצאה")
    case_access(db, user, item)
    rows = db.execute(select(ApprovalInstance, ApprovalFlowDefinition).join(
        ApprovalFlowDefinition, ApprovalInstance.approval_flow_id == ApprovalFlowDefinition.id).where(
        ApprovalInstance.case_id == case_id)).all()
    return [{"id": instance.id, "system_number": instance.system_number, "name": flow.name,
             "status": instance.status, "current_step_order": instance.current_step_order,
             "tasks": [{"id": task.id, "approver_user_id": task.approver_user_id,
                        "status": task.status, "decision": task.decision, "comment": task.comment}
                       for task in db.scalars(select(ApprovalTask).where(
                           ApprovalTask.approval_instance_id == instance.id))]}
            for instance, flow in rows]


@router.post("/approval-tasks/{task_id}/decision")
def decide(task_id: uuid.UUID, data: ApprovalDecisionIn, db: DB, user: Current) -> dict[str, Any]:
    task = db.get(ApprovalTask, task_id)
    if not task or task.approver_user_id != user.id: raise HTTPException(403, "רק המאשר שנבחר רשאי להחליט")
    if task.status != "pending": raise HTTPException(409, "המשימה כבר הושלמה")
    instance = db.get(ApprovalInstance, task.approval_instance_id)
    if not instance: raise HTTPException(409, "תהליך האישור אינו זמין")
    task.status = data.decision; task.decision = data.decision; task.comment = data.comment; task.decided_at = datetime.now(UTC)
    if data.decision in {"rejected", "returned"}: instance.status = data.decision
    else:
        step = db.get(ApprovalStepDefinition, task.step_definition_id)
        if not step: raise HTTPException(409, "שלב האישור אינו זמין")
        approved = db.scalar(select(func.count()).select_from(ApprovalTask).where(
            ApprovalTask.approval_instance_id == instance.id,
            ApprovalTask.step_definition_id == task.step_definition_id,
            ApprovalTask.status == "approved")) or 0
        if approved >= step.required_approvals:
            next_step = db.scalar(select(ApprovalStepDefinition).where(
                ApprovalStepDefinition.approval_flow_id == instance.approval_flow_id,
                ApprovalStepDefinition.step_order > step.step_order).order_by(
                ApprovalStepDefinition.step_order).limit(1))
            if next_step:
                instance.current_step_order = next_step.step_order
                create_step_tasks(db, instance, next_step.step_order)
            else:
                instance.status = "approved"; instance.completed_at = datetime.now(UTC)
    audit(db, user, "approval_instance", instance.id, data.decision); db.commit()
    return {"status": instance.status}


@router.get("/automation-executions")
def automation_logs(environment_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    require(db, user, environment_id, "environment.rules.manage")
    rows = db.execute(select(AutomationExecutionLog).join(Case).where(
        Case.environment_id == environment_id).order_by(AutomationExecutionLog.executed_at.desc())).scalars()
    return [{column.name: getattr(row, column.name) for column in row.__table__.columns} for row in rows]


def report_query(db: DB, user: Current, environment_id: uuid.UUID | None, request_type_id: uuid.UUID | None,
                 status: str | None, search: str | None, sort: str, direction: str) -> Any:
    query = select(Case, Environment, RequestType, User).join(Environment, Case.environment_id == Environment.id).join(
        RequestType, Case.request_type_id == RequestType.id).join(User, Case.requester_id == User.id)
    if not user.is_system_admin:
        query = query.where(or_(
            Case.requester_id == user.id,
            Case.reporter_id == user.id,
            Case.assignee_id == user.id,
            Case.id.in_(select(CaseParticipant.case_id).where(CaseParticipant.user_id == user.id)),
        ))
    if environment_id: query = query.where(Case.environment_id == environment_id)
    if request_type_id: query = query.where(Case.request_type_id == request_type_id)
    if status: query = query.where(Case.status == status)
    if search: query = query.where(or_(Case.case_number.ilike(f"%{search}%"), Case.title.ilike(f"%{search}%")))
    columns = {"case_number": Case.case_number, "created_at": Case.created_at,
               "updated_at": Case.updated_at, "priority": Case.priority, "status": Case.status}
    column = columns.get(sort, Case.created_at)
    return query.order_by(column.asc() if direction == "asc" else column.desc())


def report_row(row: Any) -> dict[str, Any]:
    item, env, request_type, requester = row
    return {"case_number": item.case_number, "environment": env.name_he,
            "request_type": request_type.name_he, "title": item.title,
            "description": item.description or "", "status": item.status.value,
            "priority": item.priority, "requester": requester.display_name,
            "created_at": item.created_at.isoformat(), "updated_at": item.updated_at.isoformat()}


@router.get("/reports/cases")
def cases_report(db: DB, user: Current, environment_id: uuid.UUID | None = None,
                 request_type_id: uuid.UUID | None = None, status: str | None = None,
                 search: str | None = None, sort: str = "created_at", direction: str = "desc",
                 page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200)) -> dict[str, Any]:
    query = report_query(db, user, environment_id, request_type_id, status, search, sort, direction)
    rows = db.execute(query.offset((page - 1) * page_size).limit(page_size)).all()
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    return {"items": [report_row(row) for row in rows], "total": total, "page": page, "page_size": page_size}


def xlsx_bytes(rows: list[dict[str, Any]], filters: dict[str, str]) -> bytes:
    headers = ["מספר קריאה", "סביבה", "סוג קריאה", "נושא", "תיאור", "סטטוס", "עדיפות", "פותח", "נוצר", "עודכן"]
    keys = ["case_number", "environment", "request_type", "title", "description", "status", "priority", "requester", "created_at", "updated_at"]
    def cell(value: Any) -> str: return f'<c t="inlineStr"><is><t>{escape(str(value or ""))}</t></is></c>'
    report_rows = [headers] + [[row[key] for key in keys] for row in rows]
    sheet1 = "".join(f'<row r="{index}">{"".join(cell(value) for value in values)}</row>' for index, values in enumerate(report_rows, 1))
    filter_rows = [["שם הדוח", "דוח קריאות שירות"], ["תאריך יצוא", datetime.now(UTC).isoformat()]] + list(filters.items())
    sheet2 = "".join(f'<row r="{index}">{"".join(cell(value) for value in values)}</row>' for index, values in enumerate(filter_rows, 1))
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
        archive.writestr("_rels/.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        archive.writestr("xl/workbook.xml", '<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="קריאות" sheetId="1" r:id="rId1"/><sheet name="מסננים" sheetId="2" r:id="rId2"/></sheets></workbook>')
        archive.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/></Relationships>')
        for index, data in [(1, sheet1), (2, sheet2)]: archive.writestr(f"xl/worksheets/sheet{index}.xml", f'<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{data}</sheetData></worksheet>')
    return stream.getvalue()


@router.get("/reports/cases/export")
def export_cases(db: DB, user: Current, environment_id: uuid.UUID | None = None,
                 request_type_id: uuid.UUID | None = None, status: str | None = None,
                 search: str | None = None, sort: str = "created_at", direction: str = "desc") -> Response:
    query = report_query(db, user, environment_id, request_type_id, status, search, sort, direction)
    rows = [report_row(row) for row in db.execute(query.limit(5000)).all()]
    content = xlsx_bytes(rows, {"environment_id": str(environment_id or ""), "request_type_id": str(request_type_id or ""), "status": status or "", "search": search or "", "sort": sort, "direction": direction})
    return StreamingResponse(io.BytesIO(content), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="case-report.xlsx"'})
