import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.models import EnvironmentMembership, User


class EnvironmentManagerService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def is_environment_manager(self, user: User, environment_id: uuid.UUID) -> bool:
        if user.is_system_admin:
            return True
        return self.db.scalar(select(EnvironmentMembership.id).where(
            EnvironmentMembership.environment_id == environment_id,
            EnvironmentMembership.user_id == user.id,
            EnvironmentMembership.is_active.is_(True),
            EnvironmentMembership.is_environment_manager.is_(True),
        )) is not None

    def can_manage_locked_case(self, user: User, environment_id: uuid.UUID) -> bool:
        return self.is_environment_manager(user, environment_id)
