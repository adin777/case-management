import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.models import (
    ApprovalFlowDefinition,
    ApprovalInstance,
    AutomationRule,
    Case,
    CaseFieldDefinition,
    Environment,
    Group,
    NumberingSeries,
    PriorityDefinition,
    RequestType,
    SubPriorityDefinition,
    UserFieldDefinition,
)

PREFIXES = {
    "case": "CASE", "request_type": "RT", "case_field": "CF", "user_field": "UF",
    "user_group": "UG", "approval_flow": "AF", "approval_instance": "AI",
    "automation_rule": "AR", "priority": "PR", "sub_priority": "SP",
    "environment": "ENV",
}
NUMBERED_MODELS: dict[str, tuple[type[Any], str]] = {
    "case": (Case, "case_number"), "request_type": (RequestType, "system_number"),
    "case_field": (CaseFieldDefinition, "system_number"),
    "user_field": (UserFieldDefinition, "system_number"), "user_group": (Group, "system_number"),
    "approval_flow": (ApprovalFlowDefinition, "system_number"),
    "approval_instance": (ApprovalInstance, "system_number"),
    "automation_rule": (AutomationRule, "system_number"),
    "priority": (PriorityDefinition, "system_number"),
    "sub_priority": (SubPriorityDefinition, "system_number"),
    "environment": (Environment, "system_number"),
}


class NumberingService:
    @staticmethod
    def next(db: Session, entity_type: str, environment_id: uuid.UUID | None = None) -> str:
        if entity_type not in PREFIXES:
            raise ValueError(f"Unsupported numbering entity: {entity_type}")
        query = select(NumberingSeries).where(
            NumberingSeries.entity_type == entity_type,
            NumberingSeries.environment_id == environment_id,
            NumberingSeries.is_active.is_(True),
        )
        series = db.scalar(query.with_for_update())
        if not series and environment_id is not None:
            series = db.scalar(select(NumberingSeries).where(
                NumberingSeries.entity_type == entity_type,
                NumberingSeries.environment_id.is_(None),
                NumberingSeries.is_active.is_(True),
            ).with_for_update())
        if not series:
            series = NumberingSeries(entity_type=entity_type, environment_id=environment_id,
                                     prefix=PREFIXES[entity_type], next_number=1, padding=6)
            db.add(series)
            db.flush()
        model, field_name = NUMBERED_MODELS[entity_type]
        field = getattr(model, field_name)
        while True:
            value = f"{series.prefix}-{series.next_number:0{series.padding}d}"
            series.next_number += 1
            if db.scalar(select(model.id).where(field == value)) is None:
                break
        return value
