from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.models import Employee, EnvironmentAssignmentRule, EnvironmentMembership, GroupMember, User

ALLOWED_FIELDS = {"department", "job_title", "email_domain", "username_domain", "user_id", "group_id"}


def matches(user: User, employee: Employee | None, group_ids: set[str], conditions: list[dict]) -> bool:
    by_field: dict[str, list[str]] = {}
    for condition in conditions:
        field = condition.get("field")
        raw = condition.get("value")
        values = raw if isinstance(raw, list) else [raw]
        by_field.setdefault(str(field), []).extend(str(value).casefold() for value in values if value)
    for field, expected_values in by_field.items():
        if field not in ALLOWED_FIELDS or not expected_values:
            return False
        if field == "user_id":
            actual_values = {str(user.id).casefold()}
        elif field == "group_id":
            actual_values = {value.casefold() for value in group_ids}
        elif field == "email_domain":
            actual = user.email.rsplit("@", 1)[-1]
        elif field == "username_domain":
            actual = (user.user_principal_name or "").rsplit("@", 1)[-1]
        else:
            # Legacy manually-created users may not yet have a linked Employee row.
            # New directory-backed identities always use Employee as the source of truth.
            actual = str(getattr(employee or user, field, "") or "")
        if field not in {"user_id", "group_id"}:
            actual_values = {actual.casefold()}
        if not actual_values.intersection(expected_values):
            return False
    return bool(conditions)


def preview_rule(db: Session, conditions: list[dict]) -> list[User]:
    users = list(db.scalars(select(User).where(User.status == "active")))
    employee_ids = {user.employee_record_id for user in users if user.employee_record_id}
    employees = {row.id: row for row in db.scalars(select(Employee).where(Employee.id.in_(employee_ids)))} if employee_ids else {}
    memberships: dict[str, set[str]] = {}
    for row in db.scalars(select(GroupMember)):
        memberships.setdefault(str(row.user_id), set()).add(str(row.group_id))
    return [user for user in users if matches(user, employees.get(user.employee_record_id) if user.employee_record_id else None, memberships.get(str(user.id), set()), conditions)]


def apply_rule(db: Session, rule: EnvironmentAssignmentRule) -> dict[str, int]:
    matching = {user.id for user in preview_rule(db, rule.conditions_json)} if rule.is_active else set()
    created = removed = 0
    for user_id in matching:
        existing = db.scalar(
            select(EnvironmentMembership).where(
                EnvironmentMembership.environment_id == rule.environment_id,
                EnvironmentMembership.user_id == user_id,
                EnvironmentMembership.is_active.is_(True),
            )
        )
        if not existing:
            db.add(
                EnvironmentMembership(
                    environment_id=rule.environment_id,
                    user_id=user_id,
                    role_id=None,
                    source="rule",
                    source_rule_id=rule.id,
                    is_active=True,
                )
            )
            created += 1
    generated = list(
        db.scalars(
            select(EnvironmentMembership).where(
                EnvironmentMembership.source == "rule", EnvironmentMembership.source_rule_id == rule.id
            )
        )
    )
    for membership in generated:
        if membership.user_id not in matching:
            db.delete(membership)
            removed += 1
    return {"created": created, "removed": removed, "matched": len(matching)}


def apply_all_rules(db: Session) -> None:
    for rule in db.scalars(select(EnvironmentAssignmentRule)):
        apply_rule(db, rule)
