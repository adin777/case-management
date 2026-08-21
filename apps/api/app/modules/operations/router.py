import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update

from app.modules.api import DB, Current, audit, case_access, permissions, require
from app.modules.case_semantics.service import CaseSemanticFieldService
from app.modules.models import Case
from app.modules.operations.models import (
    CaseStatusHistory,
    Notification,
    SlaPolicy,
    WorkflowDefinition,
    WorkflowStatus,
    WorkflowTransition,
)

router = APIRouter(prefix="/api", tags=["operations"])


class WorkflowIn(BaseModel):
    name_he: str = Field(min_length=2, max_length=200)
    name_en: str | None = None
    description: str | None = None
    is_active: bool = True
    is_default: bool = False


class StatusIn(BaseModel):
    code: str = Field(pattern=r"^[a-z0-9_]+$")
    label_he: str
    label_en: str | None = None
    description: str | None = None
    color: str = "#64748b"
    sort_order: int = 0
    semantic_category: str = Field(default="open", pattern="^(open|in_progress|waiting|resolved|closed)$")
    is_initial: bool = False
    is_final: bool = False
    is_closed: bool = False
    is_active: bool = True


class TransitionIn(BaseModel):
    from_status_id: uuid.UUID
    to_status_id: uuid.UUID
    label_he: str
    description: str | None = None
    required_permission_code: str | None = None
    requires_comment: bool = False
    requires_resolution: bool = False
    is_active: bool = True
    sort_order: int = 0


class TransitionRun(BaseModel):
    comment: str | None = None
    resolution: str | None = None


class SlaIn(BaseModel):
    name_he: str
    description: str | None = None
    request_type_id: uuid.UUID | None = None
    priority_id: uuid.UUID | None = None
    response_minutes: int = Field(gt=0)
    resolution_minutes: int = Field(gt=0)
    warning_threshold_percent: int = Field(80, ge=1, le=100)
    business_calendar_id: uuid.UUID | None = None
    is_active: bool = True


def row(item: Any) -> dict[str, Any]:
    return {column.name: getattr(item, column.name) for column in item.__table__.columns}


@router.get("/environments/{environment_id}/workflows")
def workflows(environment_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    require(db, user, environment_id, "workflow.read")
    items = db.scalars(
        select(WorkflowDefinition)
        .where(WorkflowDefinition.environment_id == environment_id)
        .order_by(WorkflowDefinition.name_he)
    )
    return [row(item) for item in items]


@router.post("/environments/{environment_id}/workflows", status_code=201)
def create_workflow(environment_id: uuid.UUID, data: WorkflowIn, db: DB, user: Current) -> dict[str, Any]:
    require(db, user, environment_id, "workflow.manage")
    if data.is_default:
        db.execute(
            update(WorkflowDefinition)
            .where(WorkflowDefinition.environment_id == environment_id)
            .values(is_default=False)
        )
    item = WorkflowDefinition(
        id=uuid.uuid4(),
        system_number=f"WF-{uuid.uuid4().hex[:8].upper()}",
        environment_id=environment_id,
        created_by=user.id,
        **data.model_dump(),
    )
    db.add(item)
    audit(db, user, "workflow", item.id, "created", after=data.model_dump(mode="json"))
    db.commit()
    return row(item)


@router.patch("/workflows/{workflow_id}")
def update_workflow(workflow_id: uuid.UUID, data: WorkflowIn, db: DB, user: Current) -> dict[str, Any]:
    item = db.get(WorkflowDefinition, workflow_id)
    if not item:
        raise HTTPException(404, "Workflow not found")
    require(db, user, item.environment_id, "workflow.manage")
    before = jsonable_encoder(row(item))
    if data.is_default:
        db.execute(
            update(WorkflowDefinition)
            .where(WorkflowDefinition.environment_id == item.environment_id)
            .values(is_default=False)
        )
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    audit(db, user, "workflow", item.id, "updated", before=before, after=data.model_dump(mode="json"))
    db.commit()
    return row(item)


@router.get("/workflows/{workflow_id}/statuses")
def statuses(workflow_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    workflow = db.get(WorkflowDefinition, workflow_id)
    if not workflow:
        raise HTTPException(404, "Workflow not found")
    require(db, user, workflow.environment_id, "workflow.read")
    return [row(item) for item in db.scalars(select(WorkflowStatus).where(WorkflowStatus.workflow_id == workflow_id).order_by(WorkflowStatus.sort_order))]


@router.post("/workflows/{workflow_id}/statuses", status_code=201)
def create_status(workflow_id: uuid.UUID, data: StatusIn, db: DB, user: Current) -> dict[str, Any]:
    workflow = db.get(WorkflowDefinition, workflow_id)
    if not workflow:
        raise HTTPException(404, "Workflow not found")
    require(db, user, workflow.environment_id, "workflow.manage")
    if data.is_initial and not data.is_active:
        raise HTTPException(422, "סטטוס התחלתי חייב להיות פעיל")
    if data.is_initial:
        db.execute(update(WorkflowStatus).where(WorkflowStatus.workflow_id == workflow_id).values(is_initial=False))
    item = WorkflowStatus(id=uuid.uuid4(), workflow_id=workflow_id, **data.model_dump())
    db.add(item)
    audit(db, user, "workflow_status", item.id, "created", after=data.model_dump(mode="json"))
    db.commit()
    return row(item)


@router.patch("/workflow-statuses/{status_id}")
def update_status(status_id: uuid.UUID, data: StatusIn, db: DB, user: Current) -> dict[str, Any]:
    item = db.get(WorkflowStatus, status_id)
    if not item:
        raise HTTPException(404, "Status not found")
    workflow = db.get(WorkflowDefinition, item.workflow_id)
    if not workflow:
        raise HTTPException(409, "Workflow no longer exists")
    require(db, user, workflow.environment_id, "workflow.manage")
    if data.is_initial and not data.is_active:
        raise HTTPException(422, "סטטוס התחלתי חייב להיות פעיל")
    if data.is_initial:
        db.execute(update(WorkflowStatus).where(WorkflowStatus.workflow_id == item.workflow_id).values(is_initial=False))
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    audit(db, user, "workflow_status", item.id, "updated", after=data.model_dump(mode="json"))
    db.commit()
    return row(item)


@router.post("/workflow-statuses/{status_id}/set-initial")
def set_initial_status(status_id: uuid.UUID, db: DB, user: Current) -> dict[str, Any]:
    item = db.get(WorkflowStatus, status_id)
    if not item:
        raise HTTPException(404, "הסטטוס לא נמצא")
    workflow = db.get(WorkflowDefinition, item.workflow_id)
    if not workflow:
        raise HTTPException(409, "תהליך העבודה אינו קיים")
    require(db, user, workflow.environment_id, "workflow.manage")
    if not item.is_active:
        raise HTTPException(422, "סטטוס התחלתי חייב להיות פעיל")
    db.execute(update(WorkflowStatus).where(
        WorkflowStatus.workflow_id == item.workflow_id).values(is_initial=False))
    item.is_initial = True
    audit(db, user, "workflow_status", item.id, "set_initial")
    db.commit()
    return row(item)


@router.get("/workflows/{workflow_id}/transitions")
def transitions(workflow_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    workflow = db.get(WorkflowDefinition, workflow_id)
    if not workflow:
        raise HTTPException(404, "Workflow not found")
    require(db, user, workflow.environment_id, "workflow.read")
    return [row(item) for item in db.scalars(select(WorkflowTransition).where(WorkflowTransition.workflow_id == workflow_id).order_by(WorkflowTransition.sort_order))]


@router.post("/workflows/{workflow_id}/transitions", status_code=201)
def create_transition(workflow_id: uuid.UUID, data: TransitionIn, db: DB, user: Current) -> dict[str, Any]:
    workflow = db.get(WorkflowDefinition, workflow_id)
    if not workflow:
        raise HTTPException(404, "Workflow not found")
    require(db, user, workflow.environment_id, "workflow.manage")
    states = [db.get(WorkflowStatus, value) for value in (data.from_status_id, data.to_status_id)]
    if any(not state or state.workflow_id != workflow_id for state in states):
        raise HTTPException(422, "Transition statuses must belong to the workflow")
    item = WorkflowTransition(id=uuid.uuid4(), workflow_id=workflow_id, **data.model_dump())
    db.add(item)
    audit(db, user, "workflow_transition", item.id, "created", after=data.model_dump(mode="json"))
    db.commit()
    return row(item)


@router.patch("/workflow-transitions/{transition_id}")
def update_transition(transition_id: uuid.UUID, data: TransitionIn, db: DB, user: Current) -> dict[str, Any]:
    item = db.get(WorkflowTransition, transition_id)
    if not item:
        raise HTTPException(404, "Transition not found")
    workflow = db.get(WorkflowDefinition, item.workflow_id)
    if not workflow:
        raise HTTPException(409, "Workflow no longer exists")
    require(db, user, workflow.environment_id, "workflow.manage")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    audit(db, user, "workflow_transition", item.id, "updated", after=data.model_dump(mode="json"))
    db.commit()
    return row(item)


@router.get("/cases/{case_id}/workflow-options")
def workflow_options(case_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    item = db.get(Case, case_id)
    if not item:
        raise HTTPException(404, "Case not found")
    case_access(db, user, item)
    query = select(WorkflowTransition).where(WorkflowTransition.from_status_id == item.workflow_status_id, WorkflowTransition.is_active.is_(True))
    return [row(value) for value in db.scalars(query.order_by(WorkflowTransition.sort_order))]


@router.post("/cases/{case_id}/workflow-transitions/{transition_id}")
def run_transition(case_id: uuid.UUID, transition_id: uuid.UUID, data: TransitionRun, db: DB, user: Current) -> dict[str, Any]:
    item = db.get(Case, case_id)
    transition = db.get(WorkflowTransition, transition_id)
    if not item or not transition:
        raise HTTPException(404, "Case or transition not found")
    case_access(db, user, item)
    if transition.from_status_id != item.workflow_status_id or not transition.is_active:
        raise HTTPException(409, "המעבר אינו חוקי מהסטטוס הנוכחי")
    needed = transition.required_permission_code or "case.change_status"
    if needed not in permissions(db, user, item.environment_id):
        raise HTTPException(403, f"Missing permission: {needed}")
    if transition.requires_comment and not data.comment:
        raise HTTPException(422, "נדרשת תגובה לביצוע המעבר")
    if transition.requires_resolution and not data.resolution:
        raise HTTPException(422, "נדרש תיאור פתרון לביצוע המעבר")
    previous = item.workflow_status_id
    target = db.get(WorkflowStatus, transition.to_status_id)
    CaseSemanticFieldService(db).write(item,"case.status",transition.to_status_id)
    if target and target.is_closed:
        item.closed_at = item.resolved_at = datetime.now(UTC)
        item.sla_resolution_status = "met" if not item.resolution_due_at or item.resolved_at <= item.resolution_due_at else "breached"
    history = CaseStatusHistory(case_id=item.id, from_status_id=previous, to_status_id=transition.to_status_id, transition_id=transition.id, changed_by=user.id, comment=data.comment, automation_summary=[])
    db.add(history)
    db.add(Notification(user_id=item.requester_id, notification_type="status_changed", title_he="סטטוס הקריאה השתנה", body_he=f"הקריאה {item.case_number} עברה לסטטוס {target.label_he if target else ''}", entity_type="case", entity_id=str(item.id)))
    audit(db, user, "case", item.id, "status_changed", before={"workflow_status_id": str(previous)}, after={"workflow_status_id": str(item.workflow_status_id)})
    db.commit()
    return row(history)


@router.get("/cases/{case_id}/status-history")
def status_history(case_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    item = db.get(Case, case_id)
    if not item:
        raise HTTPException(404, "Case not found")
    case_access(db, user, item)
    require(db, user, item.environment_id, "case.read_status_history")
    return [row(value) for value in db.scalars(select(CaseStatusHistory).where(CaseStatusHistory.case_id == case_id).order_by(CaseStatusHistory.created_at.desc()))]


@router.get("/environments/{environment_id}/sla-policies")
def sla_policies(environment_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    require(db, user, environment_id, "sla.read")
    return [row(item) for item in db.scalars(select(SlaPolicy).where(SlaPolicy.environment_id == environment_id).order_by(SlaPolicy.name_he))]


@router.post("/environments/{environment_id}/sla-policies", status_code=201)
def create_sla(environment_id: uuid.UUID, data: SlaIn, db: DB, user: Current) -> dict[str, Any]:
    require(db, user, environment_id, "sla.manage")
    item = SlaPolicy(id=uuid.uuid4(), system_number=f"SLA-{uuid.uuid4().hex[:8].upper()}", environment_id=environment_id, **data.model_dump())
    db.add(item)
    audit(db, user, "sla_policy", item.id, "created", after=data.model_dump(mode="json"))
    db.commit()
    return row(item)


@router.patch("/sla-policies/{policy_id}")
def update_sla(policy_id: uuid.UUID, data: SlaIn, db: DB, user: Current) -> dict[str, Any]:
    item = db.get(SlaPolicy, policy_id)
    if not item:
        raise HTTPException(404, "SLA policy not found")
    require(db, user, item.environment_id, "sla.manage")
    before = jsonable_encoder(row(item))
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    audit(db, user, "sla_policy", item.id, "updated", before=before, after=data.model_dump(mode="json"))
    db.commit()
    return row(item)


@router.get("/notifications")
def notifications(db: DB, user: Current, unread_only: bool = False, offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100)) -> dict[str, Any]:
    query = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        query = query.where(Notification.is_read.is_(False))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.order_by(Notification.created_at.desc()).offset(offset).limit(limit))
    unread = db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == user.id, Notification.is_read.is_(False))) or 0
    return {"items": [row(item) for item in items], "total": total, "unread": unread}


@router.post("/notifications/{notification_id}/read")
def read_notification(notification_id: uuid.UUID, db: DB, user: Current) -> dict[str, Any]:
    item = db.get(Notification, notification_id)
    if not item or item.user_id != user.id:
        raise HTTPException(404, "Notification not found")
    item.is_read, item.read_at = True, datetime.now(UTC)
    db.commit()
    return row(item)


@router.post("/notifications/read-all", status_code=204)
def read_all_notifications(db: DB, user: Current) -> None:
    db.execute(update(Notification).where(Notification.user_id == user.id, Notification.is_read.is_(False)).values(is_read=True, read_at=datetime.now(UTC)))
    db.commit()
