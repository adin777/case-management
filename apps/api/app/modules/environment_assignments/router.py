import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select

from app.modules.api import DB, Current, audit, require
from app.modules.environment_assignments.service import ALLOWED_FIELDS, apply_rule, preview_rule
from app.modules.models import EnvironmentAssignmentRule

router = APIRouter(prefix="/api", tags=["environment-assignments"])


class ConditionIn(BaseModel):
    field: str
    value: str = Field(min_length=1)

    @model_validator(mode="after")
    def supported(self) -> "ConditionIn":
        if self.field not in ALLOWED_FIELDS: raise ValueError("שדה כלל אינו נתמך")
        return self


class RuleIn(BaseModel):
    name: str = Field(min_length=2)
    conditions: list[ConditionIn] = Field(min_length=1)
    is_active: bool = True


@router.get("/environments/{environment_id}/assignment-rules")
def list_rules(environment_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    require(db, user, environment_id, "environment.manage")
    return [rule_dict(row) for row in db.scalars(select(EnvironmentAssignmentRule).where(
        EnvironmentAssignmentRule.environment_id == environment_id))]


@router.post("/environments/{environment_id}/assignment-rules/preview")
def preview(environment_id: uuid.UUID, data: RuleIn, db: DB, user: Current) -> dict[str, Any]:
    require(db, user, environment_id, "environment.manage")
    users = preview_rule(db, [row.model_dump() for row in data.conditions])
    return {"matched": len(users), "users": [{"id": row.id, "display_name": row.display_name,
        "department": row.department, "job_title": row.job_title} for row in users]}


@router.post("/environments/{environment_id}/assignment-rules", status_code=201)
def create(environment_id: uuid.UUID, data: RuleIn, db: DB, user: Current) -> dict[str, Any]:
    require(db, user, environment_id, "environment.manage")
    item = EnvironmentAssignmentRule(environment_id=environment_id, name=data.name,
        conditions_json=[row.model_dump() for row in data.conditions], is_active=data.is_active, created_by=user.id)
    db.add(item); db.flush(); result = apply_rule(db, item)
    audit(db, user, "environment_assignment_rule", item.id, "created", after={**data.model_dump(), **result})
    db.commit(); return {**rule_dict(item), "apply_result": result}


@router.put("/environment-assignment-rules/{rule_id}")
def update(rule_id: uuid.UUID, data: RuleIn, db: DB, user: Current) -> dict[str, Any]:
    item = db.get(EnvironmentAssignmentRule, rule_id)
    if not item: raise HTTPException(404, "הכלל לא נמצא")
    require(db, user, item.environment_id, "environment.manage")
    item.name, item.conditions_json, item.is_active = data.name, [row.model_dump() for row in data.conditions], data.is_active
    result = apply_rule(db, item); audit(db, user, "environment_assignment_rule", item.id, "updated", after=result)
    db.commit(); return {**rule_dict(item), "apply_result": result}


def rule_dict(row: EnvironmentAssignmentRule) -> dict[str, Any]:
    return {"id": row.id, "environment_id": row.environment_id, "name": row.name,
            "conditions": row.conditions_json, "is_active": row.is_active}
