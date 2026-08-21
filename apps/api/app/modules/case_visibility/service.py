import uuid

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.modules.access.service import domain_permissions
from app.modules.case_semantics.service import CaseSemanticFieldService
from app.modules.environment_manager.service import EnvironmentManagerService
from app.modules.models import Case, CaseParticipant, Environment, User


def can_manage_locked_case(db: Session, user: User, environment_id: uuid.UUID) -> bool:
    return EnvironmentManagerService(db).can_manage_locked_case(user, environment_id)


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

    def apply(self, query: Select, *, include_participants: bool = True) -> Select:
        if self.user.is_system_admin:
            return query
        conditions = [
            Case.reporter_id == self.user.id,
            Case.requester_id == self.user.id,
            CaseSemanticFieldService(self.db).indexed_column("case.assignee") == self.user.id,
            Case.environment_id.in_(self.readable_environment_ids()),
        ]
        if include_participants:
            conditions.append(Case.id.in_(select(CaseParticipant.case_id).where(
                CaseParticipant.user_id == self.user.id
            )))
        return query.where(or_(*conditions))

    def can_view(self, item: Case) -> bool:
        query = self.apply(select(Case.id).where(Case.id == item.id))
        return self.db.scalar(query) is not None
