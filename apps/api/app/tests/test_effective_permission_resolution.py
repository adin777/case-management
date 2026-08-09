import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database.session import SessionLocal
from app.main import app
from app.modules.access.models import AccessLevelAssignment, PermissionDomain
from app.modules.access.service import EffectivePermissionService
from app.modules.api import password_hash
from app.modules.models import Environment, Group, GroupMember, User

client = TestClient(app)


def admin_headers() -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "Admin123!"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_resolution_precedence_multiple_groups_inactive_and_explanation() -> None:
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.is_system_admin.is_(True)))
        environment = db.scalar(select(Environment).where(Environment.code == "IT"))
        domain = db.get(PermissionDomain, "environments_manage")
        assert admin and environment and domain
        user = User(email=f"resolver-{uuid.uuid4()}@example.com", display_name="בדיקת הרשאות",
                    password_hash=password_hash.hash("Resolver123!"), is_active=True)
        group_view = Group(name=f"צופים {uuid.uuid4()}", is_active=True)
        group_edit = Group(name=f"עורכים {uuid.uuid4()}", is_active=True)
        db.add_all([user, group_view, group_edit]); db.flush()
        db.add_all([GroupMember(group_id=group_view.id, user_id=user.id, added_by=admin.id),
                    GroupMember(group_id=group_edit.id, user_id=user.id, added_by=admin.id),
                    AccessLevelAssignment(domain_code=domain.code, group_id=group_view.id,
                        user_id=None, environment_id=None, access_level="view", created_by=admin.id),
                    AccessLevelAssignment(domain_code=domain.code, group_id=group_edit.id,
                        user_id=None, environment_id=None, access_level="edit", created_by=admin.id)])
        db.commit()
        service = EffectivePermissionService(db)
        resolved = service.resolve(user, domain, None)
        assert resolved["effective_level"] == "edit"
        assert resolved["source_name"] == group_edit.name
        assert len(resolved["resolution_steps"]) == 2

        db.add(AccessLevelAssignment(domain_code=domain.code, user_id=user.id, group_id=None,
            environment_id=None, access_level="none", created_by=admin.id)); db.commit()
        assert service.resolve(user, domain, None)["effective_level"] == "none"
        environment_override = AccessLevelAssignment(domain_code=domain.code, user_id=user.id,
            group_id=None, environment_id=environment.id, access_level="view", created_by=admin.id)
        db.add(environment_override); db.commit()
        assert service.resolve(user, domain, environment.id)["effective_level"] == "view"
        environment_override.access_level = "none"; db.commit()
        assert service.resolve(user, domain, environment.id)["effective_level"] == "none"
        db.delete(environment_override); group_edit.is_active = False; db.commit()
        assert service.resolve(user, domain, environment.id)["effective_level"] == "none"
        assert service.resolve(admin, domain, environment.id)["effective_level"] == "edit"


def test_copy_groups_preview_and_report_permission_403() -> None:
    headers = admin_headers()
    source = client.post("/api/users", headers=headers, json={"display_name": "מקור קבוצות", "email": f"source-{uuid.uuid4()}@example.com", "password": "Source123!", "is_active": True, "is_system_admin": False}).json()
    target_email = f"target-{uuid.uuid4()}@example.com"
    target = client.post("/api/users", headers=headers, json={"display_name": "יעד קבוצות", "email": target_email, "password": "Target123!", "is_active": True, "is_system_admin": False}).json()
    group = client.post("/api/groups", headers=headers, json={"name": f"קבוצה {uuid.uuid4()}", "description": "בדיקה", "is_active": True}).json()
    assert client.put(f"/api/users/{source['id']}/groups", headers=headers, json={"group_ids": [group["id"]]}).status_code == 200
    payload = {"source_user_id": source["id"], "target_user_ids": [target["id"]], "mode": "replace_all"}
    preview = client.post("/api/user-group-memberships/copy/preview", headers=headers, json=payload)
    assert preview.status_code == 200 and preview.json()["targets"][0]["changed"] is True
    copied = client.post("/api/user-group-memberships/copy", headers=headers, json=payload)
    assert copied.status_code == 200 and copied.json()["groups"] == 1
    assert group["id"] in {row["id"] for row in client.get(f"/api/users/{target['id']}", headers=headers).json()["groups"]}

    token = client.post("/api/auth/login", json={"email": target_email, "password": "Target123!"}).json()["access_token"]
    environment = client.get("/api/environments", headers=headers).json()[0]
    denied = client.get(f"/api/reports/cases?environment_id={environment['id']}", headers={"Authorization": f"Bearer {token}"})
    assert denied.status_code == 403


def test_system_admin_automatically_receives_new_domain_and_bulk_loads_existing() -> None:
    headers = admin_headers()
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.is_system_admin.is_(True)))
        assert admin
        domain = PermissionDomain(code=f"future_{uuid.uuid4().hex[:8]}", name_he="יכולת עתידית",
            description_he="תחום שנוסף לאחר יצירת המנהל", category="מערכת", scope="global",
            view_permissions="future.read", edit_permissions="future.write", is_active=True)
        db.add(domain); db.commit()
        assert EffectivePermissionService(db).resolve(admin, domain, None)["effective_level"] == "edit"
        assert "future.write" in EffectivePermissionService(db).permission_codes(admin, None)
    user = client.post("/api/users", headers=headers, json={"display_name":"טעינת הרשאות",
        "email":f"permissions-{uuid.uuid4()}@example.com","password":"Permission123!",
        "is_active":True,"is_system_admin":False}).json()
    saved = client.post("/api/access/bulk", headers=headers, json={"subject_type":"users",
        "subject_ids":[user["id"]],"environment_id":None,"levels":{domain.code:"view"}})
    assert saved.status_code == 200
    loaded = client.get(f"/api/access/assignments?subject_type=users&subject_ids={user['id']}", headers=headers)
    assert loaded.status_code == 200 and loaded.json()["levels"][domain.code] == "view"
