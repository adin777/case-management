from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.models import EnvironmentAssignmentRule, EnvironmentMembership, User

ALLOWED_FIELDS = {"department", "job_title", "email_domain", "username_domain"}


def matches(user: User, conditions: list[dict]) -> bool:
    for condition in conditions:
        field, expected = condition.get("field"), str(condition.get("value") or "").casefold()
        if field not in ALLOWED_FIELDS or not expected: return False
        if field == "email_domain": actual = user.email.rsplit("@", 1)[-1]
        elif field == "username_domain": actual = (user.user_principal_name or "").rsplit("@", 1)[-1]
        else: actual = str(getattr(user, field, "") or "")
        if actual.casefold() != expected: return False
    return bool(conditions)


def preview_rule(db: Session, conditions: list[dict]) -> list[User]:
    return [user for user in db.scalars(select(User).where(User.status == "active")) if matches(user, conditions)]


def apply_rule(db: Session, rule: EnvironmentAssignmentRule) -> dict[str, int]:
    matching = {user.id for user in preview_rule(db, rule.conditions_json)} if rule.is_active else set()
    created = removed = 0
    for user_id in matching:
        existing = db.scalar(select(EnvironmentMembership).where(
            EnvironmentMembership.environment_id == rule.environment_id,
            EnvironmentMembership.user_id == user_id, EnvironmentMembership.is_active.is_(True)))
        if not existing:
            db.add(EnvironmentMembership(environment_id=rule.environment_id, user_id=user_id,
                role_id=None, source="rule", source_rule_id=rule.id, is_active=True)); created += 1
    generated = list(db.scalars(select(EnvironmentMembership).where(
        EnvironmentMembership.source == "rule", EnvironmentMembership.source_rule_id == rule.id)))
    for membership in generated:
        if membership.user_id not in matching: db.delete(membership); removed += 1
    return {"created": created, "removed": removed, "matched": len(matching)}


def apply_all_rules(db: Session) -> None:
    for rule in db.scalars(select(EnvironmentAssignmentRule)):
        apply_rule(db, rule)
