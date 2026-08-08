import uuid
from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.access.mapping import codes
from app.modules.access.models import AccessLevelAssignment, PermissionDomain
from app.modules.models import Group, GroupMember, User

LEVELS = {"none": 0, "view": 1, "edit": 2}


class EffectivePermissionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _user_level(self, user_id: uuid.UUID, domain_code: str, environment_id: uuid.UUID | None) -> AccessLevelAssignment | None:
        return self.db.scalar(select(AccessLevelAssignment).where(
            AccessLevelAssignment.user_id == user_id,
            AccessLevelAssignment.domain_code == domain_code,
            AccessLevelAssignment.environment_id == environment_id,
        ))

    def _group_levels(self, user_id: uuid.UUID, domain_code: str, environment_id: uuid.UUID | None) -> list[tuple[AccessLevelAssignment, Group]]:
        rows = self.db.execute(
            select(AccessLevelAssignment, Group)
            .join(Group, AccessLevelAssignment.group_id == Group.id)
            .join(GroupMember, GroupMember.group_id == Group.id)
            .where(GroupMember.user_id == user_id, Group.is_active.is_(True),
                   AccessLevelAssignment.domain_code == domain_code,
                   AccessLevelAssignment.environment_id == environment_id)
        ).all()
        return [(row[0], row[1]) for row in rows]

    def resolve(self, user: User, domain: PermissionDomain, environment_id: uuid.UUID | None) -> dict:
        steps: list[dict] = []
        if user.is_system_admin:
            return {"domain": domain.code, "domain_name": domain.name_he, "effective_level": "edit",
                    "source_type": "system_admin", "source_id": str(user.id), "source_name": "מנהל מערכת",
                    "scope": "global", "resolution_steps": [{"level": "edit", "source": "מנהל מערכת"}]}

        layers: list[tuple[str, AccessLevelAssignment | list[tuple[AccessLevelAssignment, Group]] | None, str]] = []
        if environment_id:
            layers.extend([
                ("user_environment", self._user_level(user.id, domain.code, environment_id), "environment"),
                ("group_environment", self._group_levels(user.id, domain.code, environment_id), "environment"),
            ])
        layers.extend([
            ("user_global", self._user_level(user.id, domain.code, None), "global"),
            ("group_global", self._group_levels(user.id, domain.code, None), "global"),
        ])
        for source_type, value, scope in layers:
            if isinstance(value, AccessLevelAssignment):
                steps.append({"source_type": source_type, "level": value.access_level, "scope": scope})
                return {"domain": domain.code, "domain_name": domain.name_he, "effective_level": value.access_level,
                        "source_type": source_type, "source_id": str(user.id), "source_name": "חריגת משתמש",
                        "scope": scope, "resolution_steps": steps}
            if value:
                rows = value
                winner, group = max(rows, key=lambda row: LEVELS[row[0].access_level])
                steps.extend({"source_type": source_type, "source_id": str(row[1].id),
                              "source_name": row[1].name, "level": row[0].access_level, "scope": scope}
                             for row in rows)
                return {"domain": domain.code, "domain_name": domain.name_he, "effective_level": winner.access_level,
                        "source_type": source_type, "source_id": str(group.id), "source_name": group.name,
                        "scope": scope, "resolution_steps": steps}
        return {"domain": domain.code, "domain_name": domain.name_he, "effective_level": "none",
                "source_type": "default", "source_id": None, "source_name": "אין הרשאה",
                "scope": "global", "resolution_steps": steps}

    def explain_all(self, user: User, environment_id: uuid.UUID | None) -> list[dict]:
        domains = self.db.scalars(select(PermissionDomain).where(PermissionDomain.is_active.is_(True)).order_by(PermissionDomain.sort_order))
        return [self.resolve(user, domain, environment_id) for domain in domains]

    def permission_codes(self, user: User, environment_id: uuid.UUID | None) -> set[str]:
        result: set[str] = set()
        domains = {row.code: row for row in self.db.scalars(select(PermissionDomain).where(PermissionDomain.is_active.is_(True)))}
        for resolved in self.explain_all(user, environment_id):
            if resolved["effective_level"] == "none":
                continue
            domain = domains[resolved["domain"]]
            result.update(codes(domain.view_permissions))
            if resolved["effective_level"] == "edit":
                result.update(codes(domain.edit_permissions))
        return result


def domain_permissions(db: Session, user_id: uuid.UUID, environment_id: uuid.UUID | None) -> set[str]:
    user = db.get(User, user_id)
    return EffectivePermissionService(db).permission_codes(user, environment_id) if user else set()


def replace_levels(db: Session, actor_id: uuid.UUID, subject_type: str, subject_ids: list[uuid.UUID],
                   environment_id: uuid.UUID | None, levels: Mapping[str, str]) -> None:
    field = AccessLevelAssignment.user_id if subject_type == "users" else AccessLevelAssignment.group_id
    for subject_id in subject_ids:
        existing = {row.domain_code: row for row in db.scalars(select(AccessLevelAssignment).where(
            field == subject_id, AccessLevelAssignment.environment_id == environment_id))}
        for domain_code, access_level in levels.items():
            row = existing.get(domain_code)
            if access_level == "inherit" and subject_type == "users":
                if row: db.delete(row)
            elif row:
                row.access_level = access_level
            else:
                db.add(AccessLevelAssignment(domain_code=domain_code,
                    user_id=subject_id if subject_type == "users" else None,
                    group_id=subject_id if subject_type == "groups" else None,
                    environment_id=environment_id, access_level=access_level, created_by=actor_id))
