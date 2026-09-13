import uuid
from copy import deepcopy

from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy import func, select

from app.core.config import settings
from app.database.session import SessionLocal
from app.main import app
from app.modules.models import SystemSetting, User
from app.modules.notifications.email import FakeEmailProvider
from app.modules.notifications.service import NotificationService
from app.modules.operations.models import Notification, NotificationDeliveryLog, NotificationPreference

client = TestClient(app)


def auth(email: str, password: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


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


def test_notification_api_isolates_users_and_email_settings_are_admin_only(monkeypatch: MonkeyPatch)->None:
    admin_headers = auth("admin@example.com", "Admin123!")
    agent_headers = auth("agent@example.com", "Agent123!")
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.email == "admin@example.com")); assert admin
        agent = db.scalar(select(User).where(User.email == "agent@example.com")); assert agent
        suffix = uuid.uuid4().hex
        admin_item = Notification(user_id=admin.id, notification_type=f"api_{suffix}", title_he="למנהל", body_he="פרטי", entity_type="test", entity_id=suffix)
        agent_item = Notification(user_id=agent.id, notification_type=f"api_{suffix}", title_he="למטפל", body_he="פרטי", entity_type="test", entity_id=suffix)
        db.add_all([admin_item, agent_item]); db.commit()
        admin_id, agent_id = admin_item.id, agent_item.id
        existing_setting = db.get(SystemSetting, "email_settings")
        original_setting = deepcopy(existing_setting.value_json) if existing_setting else None

    try:
        listed = client.get(f"/api/notifications?notification_type=api_{suffix}", headers=admin_headers)
        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()["items"]] == [str(admin_id)]
        assert client.put(f"/api/notifications/{agent_id}/read", headers=admin_headers).status_code == 404
        assert client.get("/api/notifications/settings/email", headers=agent_headers).status_code == 403

        monkeypatch.setattr(settings, "directory_encryption_key", "notification-test-key")
        saved = client.put("/api/notifications/settings/email", headers=admin_headers, json={
            "enabled": True, "host": "smtp.example.test", "port": 587,
            "username": "sender", "password": "write-only-secret",
            "from_address": "sender@example.test", "use_tls": True,
        })
        assert saved.status_code == 200
        assert saved.json()["password_configured"] is True
        assert "password" not in saved.json() and "encrypted_password" not in saved.json()
        reread = client.get("/api/notifications/settings/email", headers=admin_headers)
        assert reread.status_code == 200 and reread.json()["password_configured"] is True
        assert "write-only-secret" not in reread.text
    finally:
        with SessionLocal() as db:
            db.query(Notification).filter(Notification.id.in_([admin_id, agent_id])).delete(synchronize_session=False)
            setting = db.get(SystemSetting, "email_settings")
            if original_setting is None:
                if setting: db.delete(setting)
            elif setting:
                setting.value_json = original_setting
            else:
                db.add(SystemSetting(key="email_settings", value_json=original_setting))
            db.commit()
