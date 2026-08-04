import uuid
from collections.abc import Mapping

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.access.mapping import codes
from app.modules.access.models import AccessLevelAssignment, PermissionDomain
from app.modules.models import GroupMember


def domain_permissions(db: Session, user_id: uuid.UUID, environment_id: uuid.UUID) -> set[str]:
    group_ids = select(GroupMember.group_id).where(GroupMember.user_id == user_id)
    rows = db.scalars(
        select(AccessLevelAssignment).where(
            or_(AccessLevelAssignment.user_id == user_id, AccessLevelAssignment.group_id.in_(group_ids)),
            or_(AccessLevelAssignment.environment_id == environment_id, AccessLevelAssignment.environment_id.is_(None)),
        )
    )
    result: set[str] = set()
    for assignment in rows:
        if assignment.access_level == "none":
            continue
        domain = db.get(PermissionDomain, assignment.domain_code)
        if not domain or not domain.is_active:
            continue
        result.update(codes(domain.view_permissions))
        if assignment.access_level == "edit":
            result.update(codes(domain.edit_permissions))
    return result


def replace_levels(
    db: Session,
    actor_id: uuid.UUID,
    subject_type: str,
    subject_ids: list[uuid.UUID],
    environment_id: uuid.UUID | None,
    levels: Mapping[str, str],
) -> None:
    field = AccessLevelAssignment.user_id if subject_type == "users" else AccessLevelAssignment.group_id
    for subject_id in subject_ids:
        existing = {row.domain_code: row for row in db.scalars(select(AccessLevelAssignment).where(field == subject_id, AccessLevelAssignment.environment_id == environment_id))}
        for domain_code, access_level in levels.items():
            row = existing.get(domain_code)
            if row:
                row.access_level = access_level
            else:
                db.add(AccessLevelAssignment(domain_code=domain_code, user_id=subject_id if subject_type == "users" else None, group_id=subject_id if subject_type == "groups" else None, environment_id=environment_id, access_level=access_level, created_by=actor_id))
