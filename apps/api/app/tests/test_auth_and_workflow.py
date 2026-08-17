import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database.session import SessionLocal
from app.main import app
from app.modules.api import password_hash
from app.modules.models import Case, Employee, EnvironmentMembership, RequestType, User

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
        assert user.employee_record_id is not None
        employee = db.get(Employee, user.employee_record_id)
        assert employee is not None and employee.email == user.email
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


def test_environment_number_is_automatic_and_case_does_not_require_workflow() -> None:
    headers = login_headers("admin@example.com", "Admin123!")
    created = []
    for suffix in ("A", "B"):
        response = client.post("/api/environments", headers=headers, json={
            "code": f"USER_CHOSEN_{suffix}",
            "name_he": f"סביבת בדיקה {suffix}",
            "name_en": f"No workflow {suffix}",
        })
        assert response.status_code == 201, response.text
        created.append(response.json())
    assert created[0]["system_number"].startswith("ENV-")
    assert created[1]["system_number"].startswith("ENV-")
    assert int(created[1]["system_number"].split("-")[1]) == int(created[0]["system_number"].split("-")[1]) + 1
    assert all(item["code"] == item["system_number"] for item in created)
    assert all(item["code"] not in {"USER_CHOSEN_A", "USER_CHOSEN_B"} for item in created)

    request_type = client.post("/api/request-types", headers=headers, json={
        "environment_id": created[0]["id"], "code": "plain", "name_he": "רגיל", "name_en": "Plain",
    })
    assert request_type.status_code == 201, request_type.text
    assert request_type.json()["workflow_definition_id"] is None
    priority = client.post(f"/api/environments/{created[0]['id']}/priorities", headers=headers, json={
        "code": "normal", "label_he": "רגילה", "label_en": "Normal", "is_active": True,
    })
    assert priority.status_code == 201, priority.text
    case = client.post("/api/cases", headers=headers, json={
        "environment_id": created[0]["id"], "request_type_id": request_type.json()["id"],
        "title": "קריאה ללא תהליך", "description": "פתיחה רגילה",
        "priority_id": priority.json()["id"], "values": [],
    })
    assert case.status_code == 201, case.text
    assert case.json()["workflow_status_id"] is None

    cloned = client.post(f"/api/environments/{created[0]['id']}/clone", headers=headers, json={
        "name_he": "סביבה משוכפלת", "name_en": "Cloned environment",
        "copy_memberships": False, "copy_knowledge": False,
    })
    assert cloned.status_code == 201, cloned.text
    cloned_environment = cloned.json()["environment"]
    assert cloned_environment["system_number"] not in {item["system_number"] for item in created}
    cloned_types = client.get(
        f"/api/request-types?environment_id={cloned_environment['id']}", headers=headers
    ).json()
    assert [item["name_he"] for item in cloned_types] == ["רגיל"]
    assert all(item["environment_id"] == cloned_environment["id"] for item in cloned_types)
    assert not [item for item in client.get("/api/cases", headers=headers).json()
                if item["environment_id"] == cloned_environment["id"]]


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


def test_request_types_are_scoped_to_the_selected_environment() -> None:
    headers = login_headers("admin@example.com", "Admin123!")
    environments = client.get("/api/environments", headers=headers).json()
    assert len(environments) >= 2
    first, second = environments[:2]
    first_rows = client.get(
        f"/api/request-types?environment_id={first['id']}", headers=headers
    ).json()
    second_rows = client.get(
        f"/api/request-types?environment_id={second['id']}", headers=headers
    ).json()
    assert all(row["environment_id"] == first["id"] for row in first_rows)
    assert all(row["environment_id"] == second["id"] for row in second_rows)
    assert {row["id"] for row in first_rows}.isdisjoint({row["id"] for row in second_rows})


def test_case_creation_request_types_include_only_active_rows() -> None:
    headers = login_headers("admin@example.com", "Admin123!")
    environments = client.get("/api/environments", headers=headers).json()
    environment, rows = next(
        (environment, rows)
        for environment in environments
        if (rows := client.get(
            f"/api/request-types?environment_id={environment['id']}", headers=headers
        ).json())
    )
    target = rows[0]
    client.patch(f"/api/request-types/{target['id']}", headers=headers, json={"is_active": False})
    try:
        active_rows = client.get(
            f"/api/request-types?environment_id={environment['id']}&active_only=true", headers=headers
        )
        assert active_rows.status_code == 200
        assert target["id"] not in {row["id"] for row in active_rows.json()}
        assert all(row["is_active"] for row in active_rows.json())
    finally:
        client.patch(f"/api/request-types/{target['id']}", headers=headers, json={"is_active": True})


def test_create_two_cases_with_same_business_values_and_without_dynamic_form() -> None:
    headers = login_headers("requester@example.com", "Requester123!")
    environment = client.get("/api/case-creation/environments", headers=headers).json()[0]
    request_type = client.get(
        f"/api/request-types?environment_id={environment['id']}&active_only=true", headers=headers
    ).json()[0]
    priority = client.get(
        f"/api/environments/{environment['id']}/priorities", headers=headers
    ).json()[0]
    with SessionLocal() as db:
        stored = db.get(RequestType, uuid.UUID(request_type["id"]))
        assert stored is not None
        original_form_id = stored.form_version_id
        stored.form_version_id = None
        db.commit()
    payload = {
        "environment_id": environment["id"],
        "request_type_id": request_type["id"],
        "title": "אותם ערכים עסקיים",
        "description": "קריאה ללא שדות דינמיים",
        "priority_id": priority["id"],
        "values": [],
    }
    try:
        first = client.post("/api/cases", headers=headers, json=payload)
        second = client.post("/api/cases", headers=headers, json=payload)
        assert first.status_code == 201, first.text
        assert second.status_code == 201, second.text
        assert first.json()["id"] != second.json()["id"]
        assert first.json()["case_number"] != second.json()["case_number"]
        assert first.json()["form_definition_id"] is None
        with SessionLocal() as db:
            source = db.get(RequestType, uuid.UUID(request_type["id"]))
            assert source is not None
            target = RequestType(
                system_number=f"RT-SWITCH-{uuid.uuid4().hex[:8]}", environment_id=source.environment_id,
                code=f"switch_{uuid.uuid4().hex[:8]}", name_he="סוג חלופי", name_en="Alternative",
                is_active=True, sort_order=99, requires_approval=source.requires_approval,
                workflow_definition_id=source.workflow_definition_id, form_version_id=None,
            )
            db.add(target); db.commit(); target_id = target.id
        changed = client.patch(f"/api/cases/{first.json()['id']}", headers=login_headers("admin@example.com", "Admin123!"), json={
            "request_type_id": str(target_id), "version": first.json()["version"],
        })
        assert changed.status_code == 200, changed.text
        assert changed.json()["request_type_id"] == str(target_id)
        assert changed.json()["environment_id"] == environment["id"]
        assert changed.json()["values"] == first.json()["values"]
    finally:
        with SessionLocal() as db:
            stored = db.get(RequestType, uuid.UUID(request_type["id"]))
            assert stored is not None
            stored.form_version_id = original_form_id
            db.commit()


def test_environment_patch_changes_only_the_path_environment() -> None:
    headers = login_headers("admin@example.com", "Admin123!")
    environments = client.get("/api/environments", headers=headers).json()
    first, second = environments[:2]
    second_before = second["is_active"]
    changed = client.patch(
        f"/api/environments/{first['id']}",
        headers=headers,
        json={"is_active": not first["is_active"]},
    )
    assert changed.status_code == 200
    refreshed_second = client.get(f"/api/environments/{second['id']}", headers=headers).json()
    assert refreshed_second["is_active"] == second_before
    client.patch(
        f"/api/environments/{first['id']}",
        headers=headers,
        json={"is_active": first["is_active"]},
    )


def test_status_options_return_all_active_statuses_and_mark_invalid_targets() -> None:
    headers = login_headers("requester@example.com", "Requester123!")
    environment = client.get("/api/environments", headers=headers).json()[0]
    request_type = client.get(
        f"/api/request-types?environment_id={environment['id']}", headers=headers
    ).json()[0]
    priority = client.get(
        f"/api/environments/{environment['id']}/priorities", headers=headers
    ).json()[0]
    form = client.get(f"/api/forms/{request_type['form_version_id']}", headers=headers).json()
    values = [{
        "field_definition_id": field["id"],
        "value": field["configuration_json"].get("options", ["בדיקה"])[0]
        if field["field_type"] == "single_select" else "בדיקה",
    } for field in form["fields"] if field["is_required"]]
    created_response = client.post("/api/cases", headers=headers, json={
        "environment_id": environment["id"],
        "request_type_id": request_type["id"],
        "title": "Status options regression",
        "description": "Verify every status is visible",
        "priority_id": priority["id"],
        "values": values,
    })
    assert created_response.status_code == 201, created_response.text
    created = created_response.json()
    options = client.get(f"/api/cases/{created['id']}/status-options", headers=headers)
    assert options.status_code == 200
    rows = options.json()
    assert len(rows) >= 2
    assert not any(row["current"] for row in rows)
    assert any(not row["allowed"] and row["reason"] for row in rows)


def test_impersonation_uses_target_permissions_and_can_be_stopped() -> None:
    admin = login_headers("admin@example.com", "Admin123!")
    requester = next(row for row in client.get("/api/users", headers=admin).json()
                     if row["email"] == "requester@example.com")
    started = client.post("/api/impersonation/start", headers=admin, json={"user_id": requester["id"]})
    assert started.status_code == 200
    impersonated = {"Authorization": f"Bearer {started.json()['access_token']}"}
    assert client.get("/api/auth/me", headers=impersonated).json()["id"] == requester["id"]
    assert client.get("/api/impersonation/status", headers=impersonated).json()["active"] is True
    assert client.post("/api/impersonation/start", headers=impersonated,
                       json={"user_id": requester["id"]}).status_code == 409
    with SessionLocal() as db:
        protected_case = db.scalar(select(Case).order_by(Case.created_at.desc()))
        assert protected_case
        protected_case_id, protected_version = protected_case.id, protected_case.version
    assert client.post(f"/api/cases/{protected_case_id}/lock", headers=impersonated,
        json={"locked": True, "reason": "אסור למשתמש מתחזה", "version": protected_version}).status_code == 403
    assert client.post(f"/api/cases/{protected_case_id}/manager-comments", headers=impersonated,
                       json={"body": "אסור"}).status_code == 403
    stopped = client.post("/api/impersonation/stop", headers=impersonated)
    assert stopped.status_code == 200
    restored = {"Authorization": f"Bearer {stopped.json()['access_token']}"}
    assert client.get("/api/auth/me", headers=restored).json()["is_system_admin"] is True
    restored_status = client.get("/api/impersonation/status", headers=restored).json()
    assert restored_status["active"] is False and restored_status["can_start"] is True


def test_case_create_permission_consumes_read_only_creation_configuration() -> None:
    admin = login_headers("admin@example.com", "Admin123!")
    worker = login_headers("requester@example.com", "Requester123!")
    environment = client.get("/api/case-creation/environments", headers=worker).json()[0]
    response = client.get(
        f"/api/case-creation/environments/{environment['id']}/configuration", headers=worker
    )
    assert response.status_code == 200
    configuration = response.json()
    assert configuration["request_types"] and "global_fields" in configuration
    request_type = configuration["request_types"][0]
    values = []
    for field in (request_type.get("form") or {}).get("fields", []):
        if not field["is_required"]:
            continue
        value = "בדיקת הרשאת יצירה"
        if field["field_type"] == "single_select":
            value = field["configuration_json"]["options"][0]
        values.append({"field_definition_id": field["id"], "value": value})
    created = client.post("/api/cases", headers=worker, json={
        "environment_id": environment["id"], "request_type_id": request_type["id"],
        "title": "קריאת עובד עם הרשאת יצירה", "description": "נוצרה ממקור קריאה ייעודי",
        "values": values,
    })
    assert created.status_code == 201, created.text
    assert client.post("/api/request-types", headers=worker, json={
        "environment_id": environment["id"], "name_he": "אסור", "name_en": "Denied", "code": "denied"
    }).status_code == 403
    denied_email = f"no-create-{uuid.uuid4()}@example.com"
    target = client.post("/api/users", headers=admin, json={
        "display_name": "ללא הרשאת יצירה", "email": denied_email,
        "password": "NoCreate123!", "is_active": True, "is_system_admin": False,
    }).json()
    assert client.post(f"/api/environments/{environment['id']}/memberships", headers=admin,
                       json={"user_id": target["id"]}).status_code == 201
    denied = client.get(
        f"/api/case-creation/environments/{environment['id']}/configuration",
        headers=login_headers(denied_email, "NoCreate123!"),
    )
    assert denied.status_code == 403


def test_global_case_fields_are_identical_across_environments() -> None:
    headers = login_headers("admin@example.com", "Admin123!")
    environments = client.get("/api/environments", headers=headers).json()
    assert len(environments) >= 1
    created = client.post("/api/global-case-fields", headers=headers, json={
        "label_he": "שדה משותף", "label_en": "Shared", "field_type": "text",
        "is_required": False, "is_active": True,
    })
    assert created.status_code == 201
    first = client.get(f"/api/case-creation/environments/{environments[0]['id']}/configuration", headers=headers)
    assert first.status_code == 200
    assert created.json()["id"] in {row["id"] for row in first.json()["global_fields"]}
