import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database.session import SessionLocal
from app.main import app
from app.modules.api import permissions
from app.modules.models import User

client = TestClient(app)


def auth(email: str, password: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def it_environment(headers: dict[str, str]) -> dict:
    return next(row for row in client.get("/api/environments", headers=headers).json() if row["code"] == "IT")


def create_case(headers: dict[str, str], participant_ids: list[str] | None = None) -> dict:
    environment = it_environment(headers)
    request_type = client.get(
        f"/api/request-types?environment_id={environment['id']}", headers=headers
    ).json()[0]
    form = client.get(f"/api/forms/{request_type['form_version_id']}", headers=headers).json()
    priority = client.get(
        f"/api/environments/{environment['id']}/priorities", headers=headers
    ).json()[1]
    values = []
    for field in form["fields"]:
        value = "Test value"
        if field["field_type"] == "single_select":
            value = field["configuration_json"]["options"][0]
        values.append({"field_definition_id": field["id"], "value": value})
    response = client.post(
        "/api/cases",
        headers=headers,
        json={
            "environment_id": environment["id"],
            "request_type_id": request_type["id"],
            "title": "Governance permission case",
            "description": "Required core description",
            "priority_id": priority["id"],
            "participant_ids": participant_ids or [],
            "values": values,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_system_administrator_can_create_user() -> None:
    response = client.post(
        "/api/users",
        headers=auth("admin@example.com", "Admin123!"),
        json={"display_name": "Governed User", "email": "governed@example.com",
              "password": "Governed123!", "is_active": True, "is_system_admin": False},
    )
    assert response.status_code == 201
    assert response.json()["is_system_admin"] is False


def test_environment_admin_cannot_create_system_administrator() -> None:
    response = client.post(
        "/api/users",
        headers=auth("envadmin@example.com", "EnvAdmin123!"),
        json={"display_name": "Forbidden Admin", "email": "forbidden.admin@example.com",
              "password": "Forbidden123!", "is_active": True, "is_system_admin": True},
    )
    assert response.status_code == 403


def test_environment_admin_manages_only_a_user_in_own_environment() -> None:
    admin_headers = auth("admin@example.com", "Admin123!")
    envadmin_headers = auth("envadmin@example.com", "EnvAdmin123!")
    environment = it_environment(envadmin_headers)
    requester = next(row for row in client.get("/api/users", headers=admin_headers).json()
                     if row["email"] == "requester@example.com")
    own = client.patch(
        f"/api/users/{requester['id']}", headers=envadmin_headers,
        json={"display_name": "משתמש קצה", "environment_id": environment["id"]},
    )
    assert own.status_code == 200
    other = client.post(
        "/api/environments", headers=admin_headers,
        json={"code": "OTHER", "name_he": "אחרת", "name_en": "Other", "description": "Other"},
    ).json()
    denied = client.patch(
        f"/api/users/{requester['id']}", headers=envadmin_headers,
        json={"display_name": "Denied", "environment_id": other["id"]},
    )
    assert denied.status_code == 403


def test_group_permissions_are_unioned_and_removed_with_membership() -> None:
    headers = auth("admin@example.com", "Admin123!")
    environment = it_environment(headers)
    requester = next(row for row in client.get("/api/users", headers=headers).json()
                     if row["email"] == "requester@example.com")
    group = client.post("/api/groups", headers=headers,
                        json={"name": "Permission Test Group", "description": "Test", "is_active": True}).json()
    role = client.post("/api/roles", headers=headers, json={
        "code": "group_assign_test", "name": "Group Assign Test", "scope": "environment",
        "description": "Test role", "permissions": ["case.assign"],
    }).json()
    assert client.post(f"/api/groups/{group['id']}/members", headers=headers,
                       json={"user_id": requester["id"]}).status_code == 201
    assert client.post(f"/api/groups/{group['id']}/roles", headers=headers,
                       json={"environment_id": environment["id"], "role_id": role["id"]}).status_code == 201
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "requester@example.com"))
        assert user and "case.assign" in permissions(db, user, uuid.UUID(environment["id"]))
    assert client.delete(f"/api/groups/{group['id']}/members/{requester['id']}", headers=headers).status_code == 204
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "requester@example.com"))
        assert user and "case.assign" not in permissions(db, user, uuid.UUID(environment["id"]))


def test_participant_access_public_comments_and_manager_isolation() -> None:
    admin_headers = auth("admin@example.com", "Admin123!")
    participant = client.post("/api/users", headers=admin_headers, json={
        "display_name": "Case Participant", "email": "participant@example.com",
        "password": "Participant123!", "is_active": True, "is_system_admin": False,
    }).json()
    outsider = client.post("/api/users", headers=admin_headers, json={
        "display_name": "Case Outsider", "email": "outsider@example.com",
        "password": "Outsider123!", "is_active": True, "is_system_admin": False,
    }).json()
    requester_headers = auth("requester@example.com", "Requester123!")
    participant_headers = auth("participant@example.com", "Participant123!")
    outsider_headers = auth("outsider@example.com", "Outsider123!")
    case = create_case(requester_headers, [participant["id"]])
    assert client.get(f"/api/cases/{case['id']}", headers=requester_headers).status_code == 200
    assert client.get(f"/api/cases/{case['id']}", headers=participant_headers).status_code == 200
    assert client.get(f"/api/cases/{case['id']}", headers=outsider_headers).status_code == 403
    assert client.post(f"/api/cases/{case['id']}/public-comments", headers=participant_headers,
                       json={"body": "Participant public reply"}).status_code == 201
    assert client.get(f"/api/cases/{case['id']}/manager-comments", headers=participant_headers).status_code == 403
    assert client.get(f"/api/cases/{case['id']}/manager-comments",
                      headers=auth("agent@example.com", "Agent123!")).status_code == 403
    envadmin_headers = auth("envadmin@example.com", "EnvAdmin123!")
    assert client.post(f"/api/cases/{case['id']}/manager-comments", headers=envadmin_headers,
                       json={"body": "Environment manager only"}).status_code == 201
    assert client.get(f"/api/cases/{case['id']}/manager-comments", headers=envadmin_headers).status_code == 200
    assert client.get(f"/api/cases/{case['id']}/manager-comments", headers=admin_headers).status_code == 200
    assert outsider["email"] == "outsider@example.com"


def test_environment_field_catalog_boundaries() -> None:
    admin_headers = auth("admin@example.com", "Admin123!")
    envadmin_headers = auth("envadmin@example.com", "EnvAdmin123!")
    environment = it_environment(envadmin_headers)
    field = client.post("/api/user-fields", headers=admin_headers, json={
        "key": "employee_number", "label_he": "מספר עובד", "label_en": "Employee number",
        "field_type": "short_text", "is_required": False, "is_active": True,
        "options_json": [], "default_value_json": None, "validation_json": {}, "sort_order": 1,
    }).json()
    selected = client.put(f"/api/environments/{environment['id']}/user-fields", headers=envadmin_headers,
                          json=[{"user_field_definition_id": field["id"], "is_visible": True,
                                 "is_required": True, "is_editable_by_user": True,
                                 "is_editable_by_environment_admin": True, "sort_order": 1}])
    assert selected.status_code == 200
    assert client.post("/api/user-fields", headers=envadmin_headers, json={
        "key": "forbidden_global", "label_he": "אסור", "label_en": "Forbidden",
        "field_type": "short_text"}).status_code == 403


def test_sub_priority_parent_and_required_core_fields() -> None:
    headers = auth("admin@example.com", "Admin123!")
    environment = it_environment(headers)
    priorities = client.get(f"/api/environments/{environment['id']}/priorities", headers=headers).json()
    high = next(row for row in priorities if row["code"] == "high")
    normal = next(row for row in priorities if row["code"] == "normal")
    assert all(row["priority_id"] == high["id"] for row in high["sub_priorities"])
    request_type = client.get(f"/api/request-types?environment_id={environment['id']}", headers=headers).json()[0]
    missing_core = client.post("/api/cases", headers=headers, json={
        "environment_id": environment["id"], "request_type_id": request_type["id"], "title": "Missing",
        "values": [],
    })
    assert missing_core.status_code == 422
    mismatched = client.post("/api/cases", headers=headers, json={
        "environment_id": environment["id"], "request_type_id": request_type["id"],
        "title": "Mismatched priority", "description": "Core description",
        "priority_id": normal["id"], "sub_priority_id": high["sub_priorities"][0]["id"], "values": [],
    })
    assert mismatched.status_code == 422
