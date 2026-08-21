import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import case as sql_case
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.case_semantics.service import CaseSemanticFieldService
from app.modules.global_case_values.service import initial_status
from app.modules.models import Case, GlobalStatusDefinition, RequestType, User
from app.modules.operations.models import SlaPolicy, WorkflowDefinition, WorkflowStatus


def ensure_environment_statuses(
    db: Session, environment_id: uuid.UUID, created_by: uuid.UUID | None = None
) -> tuple[WorkflowDefinition, WorkflowStatus]:
    """Use the legacy workflow tables as storage without requiring workflow setup."""
    workflow = db.scalar(select(WorkflowDefinition).where(
        WorkflowDefinition.environment_id == environment_id,
        WorkflowDefinition.is_default.is_(True),
        WorkflowDefinition.is_active.is_(True),
    ))
    if not workflow:
        owner_id = created_by or db.scalar(select(User.id).order_by(User.is_system_admin.desc(), User.created_at))
        if not owner_id:
            raise HTTPException(409, "לא ניתן ליצור סטטוס התחלתי ללא משתמש מערכת")
        workflow = WorkflowDefinition(
            system_number=f"WF-{str(environment_id).replace('-', '')[:8].upper()}",
            environment_id=environment_id, name_he="סטטוסים", name_en="Statuses",
            description="תצורת הסטטוסים הפנימית של הסביבה", is_active=True,
            is_default=True, created_by=owner_id,
        )
        db.add(workflow)
        db.flush()
    initial = db.scalar(select(WorkflowStatus).where(
        WorkflowStatus.workflow_id == workflow.id,
        WorkflowStatus.is_initial.is_(True),
        WorkflowStatus.is_active.is_(True),
    ))
    if not initial:
        initial = WorkflowStatus(
            workflow_id=workflow.id, code="open", label_he="פתוח", label_en="Open",
            description=None, color="#2563eb", sort_order=0, semantic_category="open",
            is_initial=True, is_final=False, is_closed=False, is_active=True,
        )
        db.add(initial)
        db.flush()
    global_initial = db.scalar(select(GlobalStatusDefinition).where(
        GlobalStatusDefinition.is_initial.is_(True), GlobalStatusDefinition.is_active.is_(True)))
    if not global_initial:
        existing = db.get(GlobalStatusDefinition, initial.id)
        if existing:
            existing.is_initial = True
        else:
            db.add(GlobalStatusDefinition(
                id=initial.id, code=f"legacy_{initial.code}_{str(initial.id).replace('-', '')[:8]}",
                label_he=initial.label_he, label_en=initial.label_en,
                semantic_category=initial.semantic_category, is_active=True, is_initial=True,
                is_final=initial.is_final, sort_order=initial.sort_order, color=initial.color,
            ))
        db.flush()
    return workflow, initial


def resolve_workflow(db: Session, request_type: RequestType) -> tuple[WorkflowDefinition, WorkflowStatus]:
    workflow = (
        db.get(WorkflowDefinition, request_type.workflow_definition_id)
        if request_type.workflow_definition_id else None
    )
    if not workflow or not workflow.is_active:
        workflow = db.scalar(
            select(WorkflowDefinition).where(
                WorkflowDefinition.environment_id == request_type.environment_id,
                WorkflowDefinition.is_default.is_(True),
                WorkflowDefinition.is_active.is_(True),
            )
        )
    if not workflow:
        return ensure_environment_statuses(db, request_type.environment_id)
    initial = db.scalar(
        select(WorkflowStatus).where(
            WorkflowStatus.workflow_id == workflow.id,
            WorkflowStatus.is_initial.is_(True),
            WorkflowStatus.is_active.is_(True),
        )
    )
    if not initial:
        return ensure_environment_statuses(db, request_type.environment_id)
    return workflow, initial


def resolve_sla(db: Session, item: Case) -> SlaPolicy | None:
    priority_id=CaseSemanticFieldService(db).value_id(item,"case.priority")
    request_match = sql_case((SlaPolicy.request_type_id == item.request_type_id, 2), else_=0)
    priority_match = sql_case((SlaPolicy.priority_id == priority_id, 1), else_=0)
    return db.scalar(
        select(SlaPolicy)
        .where(
            SlaPolicy.environment_id == item.environment_id,
            SlaPolicy.is_active.is_(True),
            (SlaPolicy.request_type_id.is_(None) | (SlaPolicy.request_type_id == item.request_type_id)),
            (SlaPolicy.priority_id.is_(None) | (SlaPolicy.priority_id == priority_id)),
        )
        .order_by((request_match + priority_match).desc(), SlaPolicy.updated_at.desc())
    )


def initialize_operations(db: Session, item: Case, request_type: RequestType) -> GlobalStatusDefinition:
    """Initialize status and SLA without requiring an active workflow."""
    initial = initial_status(db)
    CaseSemanticFieldService(db).write(item, "case.status", initial.id)
    initialize_sla(db, item)
    return initial


def initialize_sla(db: Session, item: Case) -> None:
    """Start SLA timers without reading or changing the Case status."""
    policy = resolve_sla(db, item)
    if policy:
        now = datetime.now(UTC)
        item.sla_policy_id = policy.id
        item.response_due_at = now + timedelta(minutes=policy.response_minutes)
        item.resolution_due_at = now + timedelta(minutes=policy.resolution_minutes)
        item.sla_response_status = "on_track"
        item.sla_resolution_status = "on_track"
