from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database.session import SessionLocal
from app.main import app
from app.modules.api import password_hash
from app.modules.models import EnvironmentMembership, User

client = TestClient(app)


def test_valid_login_and_current_user() -> None:
    response = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "Admin123!"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["is_system_admin"] is True


def test_invalid_login() -> None:
    assert (
        client.post("/api/auth/login", json={"email": "admin@example.com", "password": "wrong"}).status_code
        == 401
    )


def test_inactive_user_cannot_login() -> None:
    with SessionLocal() as db:
        user = User(
            email="inactive@example.com",
            display_name="Inactive",
            password_hash=password_hash.hash("Inactive123!"),
            is_active=False,
        )
        db.add(user)
        db.commit()
    assert (
        client.post(
            "/api/auth/login", json={"email": "inactive@example.com", "password": "Inactive123!"}
        ).status_code
        == 401
    )


def test_registration_hashes_password_and_assigns_requester() -> None:
    response = client.post(
        "/api/auth/register",
        json={"display_name": "New Requester", "email": "new.requester@example.com", "password": "Secure123"},
    )
    assert response.status_code == 201
    assert response.json()["access_token"] and response.json()["refresh_token"]
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "new.requester@example.com"))
        assert user is not None and user.is_active and not user.is_system_admin
        assert user.password_hash != "Secure123" and password_hash.verify("Secure123", user.password_hash)
        membership = db.scalar(select(EnvironmentMembership).where(EnvironmentMembership.user_id == user.id))
        assert membership is not None


def test_registration_rejects_duplicate_and_weak_password() -> None:
    duplicate = client.post(
        "/api/auth/register",
        json={"display_name": "Duplicate", "email": "new.requester@example.com", "password": "Secure123"},
    )
    assert duplicate.status_code == 409
    weak = client.post(
        "/api/auth/register",
        json={"display_name": "Weak", "email": "weak@example.com", "password": "password"},
    )
    assert weak.status_code == 422


def test_anonymous_access_is_blocked() -> None:
    assert client.get("/api/environments").status_code == 401


def test_admin_can_create_environment_and_audit_is_written() -> None:
    login = client.post(
        "/api/auth/login", json={"email": "admin@example.com", "password": "Admin123!"}
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    response = client.post(
        "/api/environments",
        headers=headers,
        json={
            "code": "QA_TEST",
            "name_he": "בדיקות",
            "name_en": "Quality Tests",
            "description": "Integration test",
        },
    )
    assert response.status_code in (201, 409)
    audit = client.get("/api/audit", headers=headers)
    assert audit.status_code == 200


def login_headers(email: str, password: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_complete_case_flow_and_internal_comment_filtering() -> None:
    admin_headers = login_headers("admin@example.com", "Admin123!")
    requester_headers = login_headers("requester@example.com", "Requester123!")
    agent_headers = login_headers("agent@example.com", "Agent123!")
    envadmin_headers = login_headers("envadmin@example.com", "EnvAdmin123!")
    environment = client.get("/api/environments", headers=requester_headers).json()[0]
    request_type = client.get(
        f"/api/request-types?environment_id={environment['id']}", headers=requester_headers
    ).json()[0]
    form = client.get(f"/api/forms/{request_type['form_version_id']}", headers=requester_headers).json()
    priority = client.get(
        f"/api/environments/{environment['id']}/priorities", headers=requester_headers
    ).json()[1]
    values = []
    for field in form["fields"]:
        value = "Headquarters"
        if field["field_type"] == "single_select":
            value = field["configuration_json"]["options"][0]
        values.append({"field_definition_id": field["id"], "value": value})
    created = client.post(
        "/api/cases",
        headers=requester_headers,
        json={
            "environment_id": environment["id"],
            "request_type_id": request_type["id"],
            "title": "Integration test request",
            "description": "Persistent SQLite case",
            "priority_id": priority["id"],
            "values": values,
        },
    )
    assert created.status_code == 201
    case = created.json()
    assert case["case_number"].startswith("CASE-")
    detail = client.get(f"/api/cases/{case['id']}", headers=requester_headers).json()
    assert len(detail["values"]) == len(values)

    users = client.get("/api/users", headers=admin_headers).json()
    agent = next(user for user in users if user["email"] == "agent@example.com")
    assigned = client.post(
        f"/api/cases/{case['id']}/assign",
        headers=envadmin_headers,
        json={"assignee_id": agent["id"], "version": case["version"]},
    )
    assert assigned.status_code == 200
    allowed = client.get(f"/api/cases/{case['id']}/allowed-transitions", headers=agent_headers).json()
    assert allowed
    transitioned = client.post(
        f"/api/cases/{case['id']}/transitions",
        headers=agent_headers,
        json={"workflow_status_id": allowed[0]["id"]},
    )
    assert transitioned.status_code == 200
    assert client.post(
        f"/api/cases/{case['id']}/manager-comments",
        headers=agent_headers,
        json={"body": "Internal diagnostic"},
    ).status_code == 403
    assert client.post(
        f"/api/cases/{case['id']}/manager-comments",
        headers=envadmin_headers,
        json={"body": "Manager diagnostic"},
    ).status_code == 201
    requester_detail = client.get(f"/api/cases/{case['id']}", headers=requester_headers).json()
    assert all(comment["visibility"] == "public" for comment in requester_detail["comments"])
    assert client.get(f"/api/cases/{case['id']}/manager-comments", headers=agent_headers).status_code == 403
    manager_comments = client.get(
        f"/api/cases/{case['id']}/manager-comments", headers=envadmin_headers
    ).json()
    assert manager_comments[0]["body"] == "Manager diagnostic"


def test_published_form_is_immutable_and_can_be_cloned() -> None:
    admin_headers = login_headers("admin@example.com", "Admin123!")
    environment = next(
        item for item in client.get("/api/environments", headers=admin_headers).json() if item["code"] == "IT"
    )
    request_type = client.get(
        f"/api/request-types?environment_id={environment['id']}", headers=admin_headers
    ).json()[0]
    published_id = request_type["form_version_id"]
    published = client.get(f"/api/forms/{published_id}", headers=admin_headers).json()
    assert (
        client.patch(
            f"/api/forms/{published_id}", headers=admin_headers, json={"fields": published["fields"]}
        ).status_code
        == 409
    )
    clone = client.post(f"/api/forms/{published_id}/clone-draft", headers=admin_headers)
    assert clone.status_code == 201 and clone.json()["status"] == "draft"
