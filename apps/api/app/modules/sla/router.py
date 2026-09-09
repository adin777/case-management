import io
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.modules.api import DB, Current, audit, case_access, permissions, require
from app.modules.case_semantics.service import CaseSemanticFieldService
from app.modules.environment_manager.service import EnvironmentManagerService
from app.modules.models import (
    Case,
    Environment,
    EnvironmentMembership,
    GlobalCaseFieldDefinition,
    GlobalCaseFieldOption,
    RequestType,
    User,
)
from app.modules.operations.models import BusinessCalendar, SlaInstance, SlaPause, SlaPolicy
from app.modules.sla.service import BusinessCalendarService, SlaEngine, aware

router = APIRouter(prefix="/api", tags=["sla"])


class CalendarIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    timezone: str = "Asia/Jerusalem"
    schedule_json: dict[str, list[list[str]]]
    holidays_json: list[str] = Field(default_factory=list)
    exceptions_json: dict[str, list[list[str]]] = Field(default_factory=dict)
    is_active: bool = True


def row(item: Any) -> dict[str, Any]:
    return jsonable_encoder({column.name: getattr(item, column.name) for column in item.__table__.columns})


def can_view(db: DB, user: Current, environment_id: uuid.UUID, permission: str = "sla.view") -> None:
    if user.is_system_admin or EnvironmentManagerService(db).is_environment_manager(user, environment_id):
        return
    require(db, user, environment_id, permission)


def report_environment_ids(db: DB, user: Current) -> list[uuid.UUID]:
    if user.is_system_admin:
        return list(db.scalars(select(Environment.id)))
    return [
        environment.id
        for environment in db.scalars(select(Environment))
        if "sla.report" in permissions(db, user, environment.id)
        or EnvironmentManagerService(db).is_environment_manager(user, environment.id)
    ]


@router.get("/reports/sla/options")
def sla_report_options(db: DB, user: Current) -> dict[str, Any]:
    environment_ids = report_environment_ids(db, user)
    environments = (
        list(
            db.scalars(
                select(Environment).where(Environment.id.in_(environment_ids)).order_by(Environment.name_he)
            )
        )
        if environment_ids
        else []
    )
    request_types = (
        list(
            db.scalars(
                select(RequestType)
                .where(RequestType.environment_id.in_(environment_ids), RequestType.is_active.is_(True))
                .order_by(RequestType.name_he)
            )
        )
        if environment_ids
        else []
    )
    policies = (
        list(
            db.scalars(
                select(SlaPolicy)
                .where(SlaPolicy.environment_id.in_(environment_ids))
                .order_by(SlaPolicy.name_he)
            )
        )
        if environment_ids
        else []
    )
    user_ids = (
        list(
            db.scalars(
                select(EnvironmentMembership.user_id)
                .where(
                    EnvironmentMembership.environment_id.in_(environment_ids),
                    EnvironmentMembership.user_id.is_not(None),
                    EnvironmentMembership.is_active.is_(True),
                )
                .distinct()
            )
        )
        if environment_ids
        else []
    )
    users = (
        list(
            db.scalars(
                select(User).where(User.id.in_(user_ids), User.is_active.is_(True)).order_by(User.display_name)
            )
        )
        if user_ids
        else []
    )
    priority_field = db.scalar(
        select(GlobalCaseFieldDefinition).where(
            GlobalCaseFieldDefinition.semantic_binding == "case.priority",
            GlobalCaseFieldDefinition.is_active.is_(True),
        )
    )
    priorities = (
        list(
            db.scalars(
                select(GlobalCaseFieldOption)
                .where(
                    GlobalCaseFieldOption.global_field_id == priority_field.id,
                    GlobalCaseFieldOption.is_active.is_(True),
                )
                .order_by(GlobalCaseFieldOption.sort_order)
            )
        )
        if priority_field
        else []
    )
    return {
        "environments": [{"id": item.id, "label": item.name_he} for item in environments],
        "request_types": [
            {"id": item.id, "environment_id": item.environment_id, "label": item.name_he}
            for item in request_types
        ],
        "priorities": [{"id": item.id, "label": item.label_he} for item in priorities],
        "assignees": [{"id": item.id, "label": item.display_name} for item in users],
        "policies": [
            {"id": item.id, "environment_id": item.environment_id, "label": item.name_he} for item in policies
        ],
    }


@router.get("/environments/{environment_id}/business-calendars")
def calendars(environment_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    can_view(db, user, environment_id)
    return [
        row(item)
        for item in db.scalars(
            select(BusinessCalendar)
            .where(BusinessCalendar.environment_id == environment_id)
            .order_by(BusinessCalendar.name)
        )
    ]


@router.post("/environments/{environment_id}/business-calendars", status_code=201)
def create_calendar(environment_id: uuid.UUID, data: CalendarIn, db: DB, user: Current) -> dict[str, Any]:
    require(db, user, environment_id, "sla.configure")
    if not any(data.schedule_json.values()):
        raise HTTPException(422, "Business calendar must include at least one working interval")
    try:
        BusinessCalendarService(BusinessCalendar(timezone=data.timezone)).timezone()
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    item = BusinessCalendar(environment_id=environment_id, **data.model_dump())
    db.add(item)
    db.flush()
    audit(db, user, "business_calendar", item.id, "created", after=data.model_dump(mode="json"))
    db.commit()
    return row(item)


@router.put("/business-calendars/{calendar_id}")
def update_calendar(calendar_id: uuid.UUID, data: CalendarIn, db: DB, user: Current) -> dict[str, Any]:
    item = db.get(BusinessCalendar, calendar_id)
    if not item:
        raise HTTPException(404, "לוח העבודה לא נמצא")
    require(db, user, item.environment_id, "sla.configure")
    if not any(data.schedule_json.values()):
        raise HTTPException(422, "Business calendar must include at least one working interval")
    before = row(item)
    try:
        BusinessCalendarService(BusinessCalendar(timezone=data.timezone)).timezone()
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    audit(
        db, user, "business_calendar", item.id, "updated", before=before, after=data.model_dump(mode="json")
    )
    db.commit()
    return row(item)


@router.delete("/business-calendars/{calendar_id}", status_code=204)
def delete_calendar(calendar_id: uuid.UUID, db: DB, user: Current) -> None:
    item = db.get(BusinessCalendar, calendar_id)
    if not item:
        raise HTTPException(404, "לוח העבודה לא נמצא")
    require(db, user, item.environment_id, "sla.configure")
    if db.scalar(select(SlaPolicy.id).where(SlaPolicy.business_calendar_id == item.id)):
        item.is_active = False
        audit(db, user, "business_calendar", item.id, "deactivated_used")
    else:
        audit(db, user, "business_calendar", item.id, "deleted", before=row(item))
        db.delete(item)
    db.commit()


@router.get("/cases/{case_id}/sla")
def case_sla(case_id: uuid.UUID, db: DB, user: Current) -> dict[str, Any] | None:
    item = db.get(Case, case_id)
    if not item:
        raise HTTPException(404, "הקריאה לא נמצאה")
    case_access(db, user, item)
    can_view(db, user, item.environment_id)
    instance = SlaEngine(db).active_instance(item.id)
    if not instance:
        return None
    policy = db.get(SlaPolicy, instance.policy_id)
    pauses = db.scalars(
        select(SlaPause).where(SlaPause.instance_id == instance.id).order_by(SlaPause.started_at)
    )
    return {
        **row(instance),
        "policy_name": policy.name_he if policy else "",
        "pauses": [row(value) for value in pauses],
    }


@router.post("/sla/process-due")
def process_due(db: DB, user: Current, now: datetime | None = None) -> dict[str, int]:
    if not user.is_system_admin:
        raise HTTPException(403, "רק מנהל מערכת רשאי להפעיל עיבוד SLA ידני")
    result = SlaEngine(db).tick(now)
    audit(db, user, "sla_scheduler", uuid.uuid4(), "processed", after=result)
    db.commit()
    return result


def report_query(
    db: DB,
    user: Current,
    environment_id: uuid.UUID | None,
    state: str | None,
    policy_id: uuid.UUID | None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    request_type_id: uuid.UUID | None = None,
    priority_option_id: uuid.UUID | None = None,
    assignee_id: uuid.UUID | None = None,
) -> Any:
    query = (
        select(SlaInstance, Case, SlaPolicy, Environment, RequestType)
        .join(Case, SlaInstance.case_id == Case.id)
        .join(SlaPolicy, SlaInstance.policy_id == SlaPolicy.id)
        .join(Environment, Case.environment_id == Environment.id)
        .join(RequestType, Case.request_type_id == RequestType.id)
        .where(SlaInstance.superseded_at.is_(None))
    )
    if environment_id:
        can_view(db, user, environment_id, "sla.report")
        query = query.where(Case.environment_id == environment_id)
    elif not user.is_system_admin:
        query = query.where(Case.environment_id.in_(report_environment_ids(db, user)))
    if created_from:
        query = query.where(Case.created_at >= created_from)
    if created_to:
        query = query.where(Case.created_at <= created_to)
    if request_type_id:
        query = query.where(Case.request_type_id == request_type_id)
    if priority_option_id:
        query = query.where(
            CaseSemanticFieldService(db).indexed_column("case.priority") == priority_option_id
        )
    if assignee_id:
        query = query.where(CaseSemanticFieldService(db).indexed_column("case.assignee") == assignee_id)
    if state:
        query = query.where((SlaInstance.response_status == state) | (SlaInstance.resolution_status == state))
    if policy_id:
        query = query.where(SlaInstance.policy_id == policy_id)
    return query


def report_row(values: Any) -> dict[str, Any]:
    instance, item, policy, environment, request_type = values
    return {
        "case_id": item.id,
        "case_number": item.case_number,
        "subject": item.title,
        "environment": environment.name_he,
        "request_type": request_type.name_he,
        "policy": policy.name_he,
        "response_target_minutes": policy.response_minutes,
        "response_actual": instance.first_response_at,
        "response_result": instance.response_status,
        "resolution_target_minutes": policy.resolution_minutes,
        "resolution_actual": instance.resolved_at,
        "resolution_result": instance.resolution_status,
        "paused_seconds": instance.accumulated_pause_seconds,
        "response_due_at": instance.response_due_at,
        "resolution_due_at": instance.resolution_due_at,
        "assignee_id": item.assignee_id,
    }


@router.get("/reports/sla")
def sla_report(
    db: DB,
    user: Current,
    environment_id: uuid.UUID | None = None,
    state: str | None = None,
    policy_id: uuid.UUID | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    request_type_id: uuid.UUID | None = None,
    priority_option_id: uuid.UUID | None = None,
    assignee_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> dict[str, Any]:
    query = report_query(
        db,
        user,
        environment_id,
        state,
        policy_id,
        created_from,
        created_to,
        request_type_id,
        priority_option_id,
        assignee_id,
    )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.order_by(SlaInstance.started_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {
        "items": [report_row(value) for value in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/reports/sla/metrics")
def sla_metrics(
    db: DB,
    user: Current,
    environment_id: uuid.UUID | None = None,
    state: str | None = None,
    policy_id: uuid.UUID | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    request_type_id: uuid.UUID | None = None,
    priority_option_id: uuid.UUID | None = None,
    assignee_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    rows = db.execute(
        report_query(
            db,
            user,
            environment_id,
            state,
            policy_id,
            created_from,
            created_to,
            request_type_id,
            priority_option_id,
            assignee_id,
        )
    ).all()
    instances = [value[0] for value in rows]
    response_done = [value for value in instances if value.response_status in {"met", "breached"}]
    resolution_done = [value for value in instances if value.resolution_status in {"met", "breached"}]
    response_met = sum(value.response_status == "met" for value in response_done)
    resolution_met = sum(value.resolution_status == "met" for value in resolution_done)
    completed = len(response_done) + len(resolution_done)
    met = response_met + resolution_met
    breached = sum("breached" in {value.response_status, value.resolution_status} for value in instances)
    risk = sum("warning" in {value.response_status, value.resolution_status} for value in instances)
    response_times = [
        (aware(value.first_response_at) - aware(value.started_at)).total_seconds()
        - value.accumulated_pause_seconds
        for value in instances
        if value.first_response_at
    ]
    resolution_times = [
        (aware(value.resolved_at) - aware(value.started_at)).total_seconds() - value.accumulated_pause_seconds
        for value in instances
        if value.resolved_at
    ]
    return {
        "total": len(instances),
        "compliance_percent": round(met / completed * 100, 1) if completed else 0,
        "response_compliance_percent": round(response_met / len(response_done) * 100, 1)
        if response_done
        else 0,
        "resolution_compliance_percent": round(resolution_met / len(resolution_done) * 100, 1)
        if resolution_done
        else 0,
        "breached": breached,
        "at_risk": risk,
        "average_first_response_seconds": round(sum(response_times) / len(response_times), 1)
        if response_times
        else 0,
        "average_resolution_seconds": round(sum(resolution_times) / len(resolution_times), 1)
        if resolution_times
        else 0,
        "average_paused_seconds": round(
            sum(value.accumulated_pause_seconds for value in instances) / len(instances), 1
        )
        if instances
        else 0,
    }


@router.get("/reports/sla/export")
def sla_export(
    db: DB,
    user: Current,
    environment_id: uuid.UUID | None = None,
    state: str | None = None,
    policy_id: uuid.UUID | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    request_type_id: uuid.UUID | None = None,
    priority_option_id: uuid.UUID | None = None,
    assignee_id: uuid.UUID | None = None,
) -> StreamingResponse:
    rows = [
        report_row(value)
        for value in db.execute(
            report_query(
                db,
                user,
                environment_id,
                state,
                policy_id,
                created_from,
                created_to,
                request_type_id,
                priority_option_id,
                assignee_id,
            )
        ).all()
    ]
    book = Workbook()
    sheet = book.active
    sheet.title = "SLA"
    headers = (
        list(rows[0])
        if rows
        else ["case_number", "subject", "environment", "policy", "response_result", "resolution_result"]
    )
    sheet.append(headers)
    for item in rows:
        sheet.append([str(item.get(key, "")) if item.get(key) is not None else "" for key in headers])
    stream = io.BytesIO()
    book.save(stream)
    stream.seek(0)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=sla-report.xlsx"},
    )
