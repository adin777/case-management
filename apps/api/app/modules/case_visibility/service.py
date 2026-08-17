import uuid

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.modules.access.service import domain_permissions
from app.modules.models import Case, CaseParticipant, Environment, EnvironmentMembership, User


def can_manage_locked_case(db: Session, user: User, environment_id: uuid.UUID) -> bool:
    if user.is_system_admin:
        return True
    return db.scalar(select(EnvironmentMembership.id).where(
        EnvironmentMembership.environment_id == environment_id,
        EnvironmentMembership.user_id == user.id,
        EnvironmentMembership.is_active.is_(True),
        EnvironmentMembership.is_environment_manager.is_(True),
    )) is not None


class CaseVisibilityService:
    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user

    def readable_environment_ids(self) -> list[uuid.UUID]:
        if self.user.is_system_admin:
            return list(self.db.scalars(select(Environment.id)))
        result = []
        for environment_id in self.db.scalars(select(Environment.id)):
            granted = domain_permissions(self.db, self.user.id, environment_id)
            if "case.read_environment" in granted or "case.read" in granted:
                result.append(environment_id)
        return result

    def apply(self, query: Select) -> Select:
        if self.user.is_system_admin:
            return query
        return query.where(or_(
            Case.reporter_id == self.user.id,
            Case.requester_id == self.user.id,
            Case.assignee_id == self.user.id,
            Case.environment_id.in_(self.readable_environment_ids()),
            Case.id.in_(select(CaseParticipant.case_id).where(CaseParticipant.user_id == self.user.id)),
        ))

    def can_view(self, item: Case) -> bool:
        query = self.apply(select(Case.id).where(Case.id == item.id))
        return self.db.scalar(query) is not None
