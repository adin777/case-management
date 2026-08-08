from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database.session import SessionLocal
from app.main import app
from app.modules.api import password_hash, permissions
from app.modules.models import Environment, User

client = TestClient(app)


def admin_headers() -> dict[str, str]:
    response = client.post(
        "/api/auth/login", json={"email": "admin@example.com", "password": "Admin123!"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_access_levels_and_copy_modes() -> None:
    headers = admin_headers()
    with SessionLocal() as db:
        environment = db.scalar(select(Environment).where(Environment.code == "IT"))
        assert environment is not None
        source = User(
            email="access.source@example.com",
            display_name="משתמש מקור",
            password_hash=password_hash.hash("Source123!"),
            is_active=True,
        )
        target = User(
            email="access.target@example.com",
            display_name="משתמש יעד",
            password_hash=password_hash.hash("Target123!"),
            is_active=True,
        )
        db.add_all([source, target])
        db.commit()
        source_id, target_id, environment_id = source.id, target.id, environment.id

    response = client.post(
        "/api/access/bulk",
        headers=headers,
        json={
            "subject_type": "users",
            "subject_ids": [str(source_id)],
            "environment_id": str(environment_id),
            "levels": {"cases": "view"},
        },
    )
    assert response.status_code == 200
    with SessionLocal() as db:
        stored_source = db.get(User, source_id)
        assert stored_source is not None
        assert "case.read" in permissions(db, stored_source, environment_id)
        assert "case.update" not in permissions(db, stored_source, environment_id)

    copied = client.post(
        "/api/access/copy",
        headers=headers,
        json={
            "source_type": "user",
            "source_id": str(source_id),
            "target_type": "users",
            "target_ids": [str(target_id)],
            "environment_id": str(environment_id),
            "mode": "replace",
        },
    )
    assert copied.status_code == 200 and copied.json()["domains"] == 1
    response = client.post(
        "/api/access/bulk",
        headers=headers,
        json={
            "subject_type": "users",
            "subject_ids": [str(source_id)],
            "environment_id": str(environment_id),
            "levels": {"cases": "edit"},
        },
    )
    assert response.status_code == 200
    with SessionLocal() as db:
        stored_source = db.get(User, source_id)
        stored_target = db.get(User, target_id)
        assert stored_source is not None and stored_target is not None
        assert "case.update" in permissions(db, stored_source, environment_id)
        assert "case.update" not in permissions(db, stored_target, environment_id)


def test_three_step_flow_editor_accepts_three_users() -> None:
    headers = admin_headers()
    with SessionLocal() as db:
        environment = db.scalar(select(Environment).where(Environment.code == "IT"))
        assert environment is not None
        users = list(db.scalars(select(User).limit(3)))
        while len(users) < 3:
            user = User(
                email=f"approver{len(users)}@example.com",
                display_name=f"מאשר {len(users)}",
                password_hash=password_hash.hash("Approver123!"),
                is_active=True,
            )
            db.add(user)
            db.flush()
            users.append(user)
        db.commit()
        environment_id = environment.id
        user_ids = [user.id for user in users]

    payload = {
        "name": "סבב אישורים תלת שלבי",
        "trigger_type": "case_created",
        "approval_policy": "all_active_steps",
        "steps": [
            {"name": "אישור ראשון", "approver_type": "user", "approver_user_id": str(user_ids[0])},
            {"name": "אישור שני", "approver_type": "user", "approver_user_id": str(user_ids[1])},
            {"name": "אישור סופי", "approver_type": "user", "approver_user_id": str(user_ids[2])},
        ],
    }
    created = client.post(
        f"/api/environments/{environment_id}/approval-flows", headers=headers, json=payload
    )
    assert created.status_code == 201 and len(created.json()["steps"]) == 3
    payload["name"] = "סבב אישורים תלת שלבי מעודכן"
    updated = client.put(
        f"/api/approval-flows/{created.json()['id']}", headers=headers, json=payload
    )
    assert updated.status_code == 200 and updated.json()["name"].endswith("מעודכן")
