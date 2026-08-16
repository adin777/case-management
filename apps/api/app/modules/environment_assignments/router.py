import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select

from app.modules.api import DB, Current, audit, require
from app.modules.environment_assignments.service import ALLOWED_FIELDS, apply_rule, preview_rule
from app.modules.models import Employee, EnvironmentAssignmentRule, User

router = APIRouter(prefix="/api", tags=["environment-assignments"])


class ConditionIn(BaseModel):
    field: str
    value: str | list[str]

    @model_validator(mode="after")
    def supported(self) -> "ConditionIn":
        if self.field not in ALLOWED_FIELDS:
            raise ValueError("שדה כלל אינו נתמך")
        values = self.value if isinstance(self.value, list) else [self.value]
        if not values or any(not value.strip() for value in values):
            raise ValueError("יש לבחור לפחות ערך אחד")
        return self


class RuleIn(BaseModel):
    name: str = Field(min_length=2)
    conditions: list[ConditionIn] = Field(min_length=1)
    is_active: bool = True


@router.get("/environments/{environment_id}/assignment-rules")
def list_rules(environment_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    require(db, user, environment_id, "environment.manage")
    return [
        rule_dict(row)
        for row in db.scalars(
            select(EnvironmentAssignmentRule).where(
                EnvironmentAssignmentRule.environment_id == environment_id
            )
        )
    ]


@router.get("/environment-assignment-options")
def assignment_options(db: DB, user: Current) -> dict[str, Any]:
    if not user.is_system_admin:
        raise HTTPException(403, "נדרש מנהל מערכת")
    active_users = list(db.scalars(select(User).where(User.status == "active").order_by(User.display_name)))
    active_employees = list(db.scalars(select(Employee).where(Employee.status == "active")))
    from app.modules.models import Group

    return {
        "departments": sorted({row.department.strip() for row in active_employees if row.department and row.department.strip()}),
        "job_titles": sorted({row.job_title.strip() for row in active_employees if row.job_title and row.job_title.strip()}),
        "users": [{"id": row.id, "label": row.display_name, "email": row.email} for row in active_users],
        "groups": [
            {"id": row.id, "label": row.name}
            for row in db.scalars(select(Group).where(Group.is_active.is_(True)).order_by(Group.name))
        ],
    }


@router.post("/environments/{environment_id}/assignment-rules/preview")
def preview(environment_id: uuid.UUID, data: RuleIn, db: DB, user: Current) -> dict[str, Any]:
    require(db, user, environment_id, "environment.manage")
    users = preview_rule(db, [row.model_dump() for row in data.conditions])
    return {
        "matched": len(users),
        "users": [
            {
                "id": row.id,
                "display_name": row.display_name,
                "email": row.email,
                "department": row.department,
                "job_title": row.job_title,
            }
            for row in users
        ],
    }


@router.post("/environments/{environment_id}/assignment-rules", status_code=201)
def create(environment_id: uuid.UUID, data: RuleIn, db: DB, user: Current) -> dict[str, Any]:
    require(db, user, environment_id, "environment.manage")
    item = EnvironmentAssignmentRule(
        environment_id=environment_id,
        name=data.name,
        conditions_json=[row.model_dump() for row in data.conditions],
        is_active=data.is_active,
        created_by=user.id,
    )
    db.add(item)
    db.flush()
    result = apply_rule(db, item)
    audit(db, user, "environment_assignment_rule", item.id, "created", after={**data.model_dump(), **result})
    db.commit()
    return {**rule_dict(item), "apply_result": result}


@router.put("/environment-assignment-rules/{rule_id}")
def update(rule_id: uuid.UUID, data: RuleIn, db: DB, user: Current) -> dict[str, Any]:
    item = db.get(EnvironmentAssignmentRule, rule_id)
    if not item:
        raise HTTPException(404, "הכלל לא נמצא")
    require(db, user, item.environment_id, "environment.manage")
    item.name, item.conditions_json, item.is_active = (
        data.name,
        [row.model_dump() for row in data.conditions],
        data.is_active,
    )
    result = apply_rule(db, item)
    audit(db, user, "environment_assignment_rule", item.id, "updated", after=result)
    db.commit()
    return {**rule_dict(item), "apply_result": result}


def rule_dict(row: EnvironmentAssignmentRule) -> dict[str, Any]:
    return {
        "id": row.id,
        "environment_id": row.environment_id,
        "name": row.name,
        "conditions": row.conditions_json,
        "is_active": row.is_active,
    }
