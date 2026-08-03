from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import case as sql_case
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.models import Case, RequestType
from app.modules.operations.models import SlaPolicy, WorkflowDefinition, WorkflowStatus


def resolve_workflow(db: Session, request_type: RequestType) -> tuple[WorkflowDefinition, WorkflowStatus]:
    workflow = db.get(WorkflowDefinition, request_type.workflow_definition_id)
    if not workflow or not workflow.is_active:
        workflow = db.scalar(
            select(WorkflowDefinition).where(
                WorkflowDefinition.environment_id == request_type.environment_id,
                WorkflowDefinition.is_default.is_(True),
                WorkflowDefinition.is_active.is_(True),
            )
        )
    if not workflow:
        raise HTTPException(409, "לא הוגדר תהליך עבודה לסוג הקריאה שנבחר")
    initial = db.scalar(
        select(WorkflowStatus).where(
            WorkflowStatus.workflow_id == workflow.id,
            WorkflowStatus.is_initial.is_(True),
            WorkflowStatus.is_active.is_(True),
        )
    )
    if not initial:
        raise HTTPException(409, "לא הוגדר סטטוס התחלתי לתהליך העבודה")
    return workflow, initial


def resolve_sla(db: Session, item: Case) -> SlaPolicy | None:
    request_match = sql_case((SlaPolicy.request_type_id == item.request_type_id, 2), else_=0)
    priority_match = sql_case((SlaPolicy.priority_id == item.priority_id, 1), else_=0)
    return db.scalar(
        select(SlaPolicy)
        .where(
            SlaPolicy.environment_id == item.environment_id,
            SlaPolicy.is_active.is_(True),
            (SlaPolicy.request_type_id.is_(None) | (SlaPolicy.request_type_id == item.request_type_id)),
            (SlaPolicy.priority_id.is_(None) | (SlaPolicy.priority_id == item.priority_id)),
        )
        .order_by((request_match + priority_match).desc(), SlaPolicy.updated_at.desc())
    )


def initialize_operations(db: Session, item: Case, request_type: RequestType) -> WorkflowStatus:
    _, initial = resolve_workflow(db, request_type)
    item.workflow_status_id = initial.id
    policy = resolve_sla(db, item)
    if policy:
        now = datetime.now(UTC)
        item.sla_policy_id = policy.id
        item.response_due_at = now + timedelta(minutes=policy.response_minutes)
        item.resolution_due_at = now + timedelta(minutes=policy.resolution_minutes)
        item.sla_response_status = "on_track"
        item.sla_resolution_status = "on_track"
    return initial
