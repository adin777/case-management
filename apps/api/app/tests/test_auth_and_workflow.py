from fastapi.testclient import TestClient

from app.main import app
from app.modules.api import TRANSITIONS
from app.modules.models import CaseStatus

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


def test_anonymous_access_is_blocked() -> None:
    assert client.get("/api/environments").status_code == 401


def test_transition_rules_are_centralized() -> None:
    assert CaseStatus.in_progress in TRANSITIONS[CaseStatus.submitted]
    assert CaseStatus.closed not in TRANSITIONS[CaseStatus.submitted]


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
    environment = client.get("/api/environments", headers=requester_headers).json()[0]
    request_type = client.get(
        f"/api/request-types?environment_id={environment['id']}", headers=requester_headers
    ).json()[0]
    form = client.get(f"/api/forms/{request_type['form_version_id']}", headers=requester_headers).json()
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
        headers=agent_headers,
        json={"assignee_id": agent["id"], "version": case["version"]},
    )
    assert assigned.status_code == 200
    transitioned = client.post(
        f"/api/cases/{case['id']}/transitions",
        headers=agent_headers,
        json={"status": "in_progress"},
    )
    assert transitioned.status_code == 200
    assert (
        client.post(
            f"/api/cases/{case['id']}/comments",
            headers=agent_headers,
            json={"body": "Internal diagnostic", "visibility": "internal"},
        ).status_code
        == 201
    )
    requester_detail = client.get(f"/api/cases/{case['id']}", headers=requester_headers).json()
    assert all(comment["visibility"] == "public" for comment in requester_detail["comments"])
    agent_detail = client.get(f"/api/cases/{case['id']}", headers=agent_headers).json()
    assert any(comment["visibility"] == "internal" for comment in agent_detail["comments"])


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
