import uuid

from sqlalchemy import func, select

from app.database.session import SessionLocal
from app.modules.models import User
from app.modules.notifications.email import FakeEmailProvider
from app.modules.notifications.service import NotificationService
from app.modules.operations.models import Notification, NotificationDeliveryLog, NotificationPreference


def test_notification_dedup_preferences_and_email_failure_are_isolated()->None:
    with SessionLocal() as db:
        user=db.scalar(select(User).where(User.email=="admin@example.com"));assert user
        kind=f"test_{uuid.uuid4().hex}"
        db.add(NotificationPreference(user_id=user.id,notification_type=kind,in_app_enabled=True,email_enabled=True,frequency="immediate"));db.flush()
        service=NotificationService(db);key=f"dedup:{uuid.uuid4()}"
        first=service.notify_user(user.id,kind,"כותרת","תוכן",deduplication_key=key);assert first
        assert service.notify_user(user.id,kind,"כותרת","תוכן",deduplication_key=key) is None
        result=service.deliver_pending_email(FakeEmailProvider(fail=True));assert result["failed"]>=1
        assert db.scalar(select(func.count()).select_from(Notification).where(Notification.deduplication_key==key))==1
        assert db.scalar(select(func.count()).select_from(NotificationDeliveryLog).where(NotificationDeliveryLog.notification_id==first.id))==1
        db.rollback()
