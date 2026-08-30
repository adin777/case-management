from datetime import UTC, datetime, timedelta

from sqlalchemy import case as sql_case
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.case_semantics.service import CaseSemanticFieldService
from app.modules.global_case_values.service import initial_status
from app.modules.models import Case, GlobalCaseFieldOption, RequestType
from app.modules.operations.models import SlaPolicy


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


def initialize_operations(db: Session, item: Case, request_type: RequestType) -> GlobalCaseFieldOption:
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
