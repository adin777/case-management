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
    priority = client.get(f"/api/environments/{environment['id']}/priorities", headers=headers).json()[1]
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
        json={
            "display_name": "Governed User",
            "email": "governed@example.com",
            "password": "Governed123!",
            "is_active": True,
            "is_system_admin": False,
        },
    )
    assert response.status_code == 201
    assert response.json()["is_system_admin"] is False


def test_environment_admin_cannot_create_system_administrator() -> None:
    response = client.post(
        "/api/users",
        headers=auth("envadmin@example.com", "EnvAdmin123!"),
        json={
            "display_name": "Forbidden Admin",
            "email": "forbidden.admin@example.com",
            "password": "Forbidden123!",
            "is_active": True,
            "is_system_admin": True,
        },
    )
    assert response.status_code == 403


def test_environment_admin_manages_only_a_user_in_own_environment() -> None:
    admin_headers = auth("admin@example.com", "Admin123!")
    envadmin_headers = auth("envadmin@example.com", "EnvAdmin123!")
    environment = it_environment(envadmin_headers)
    requester = next(
        row
        for row in client.get("/api/users", headers=admin_headers).json()
        if row["email"] == "requester@example.com"
    )
    own = client.patch(
        f"/api/users/{requester['id']}",
        headers=envadmin_headers,
        json={"display_name": "משתמש קצה", "environment_id": environment["id"]},
    )
    assert own.status_code == 200
    other = client.post(
        "/api/environments",
        headers=admin_headers,
        json={"code": "OTHER", "name_he": "אחרת", "name_en": "Other", "description": "Other"},
    ).json()
    denied = client.patch(
        f"/api/users/{requester['id']}",
        headers=envadmin_headers,
        json={"display_name": "Denied", "environment_id": other["id"]},
    )
    assert denied.status_code == 403


def test_global_and_environment_user_fields_are_scoped() -> None:
    headers = auth("admin@example.com", "Admin123!")
    environments = client.get("/api/environments", headers=headers).json()[:2]
    global_field = client.post("/api/user-fields", headers=headers, json={
        "key": f"global_{uuid.uuid4().hex[:8]}", "label_he": "שדה כללי", "field_type": "short_text",
        "environment_ids": [environments[0]["id"]],
    })
    assert global_field.status_code == 201, global_field.text
    assert global_field.json()["scope"] == "global"
    assert global_field.json()["environment_ids"] == [environments[0]["id"]]
    environment_field = client.post(
        f"/api/environments/{environments[0]['id']}/user-field-definitions", headers=headers, json={
            "key": f"environment_{uuid.uuid4().hex[:8]}", "label_he": "שדה סביבתי",
            "field_type": "short_text",
        })
    assert environment_field.status_code == 201, environment_field.text
    assert environment_field.json()["scope"] == "environment"
    first = client.get(f"/api/environments/{environments[0]['id']}/user-fields", headers=headers).json()
    second = client.get(f"/api/environments/{environments[1]['id']}/user-fields", headers=headers).json()
    assert any(row["definition"]["id"] == environment_field.json()["id"] for row in first)
    assert not any(row["definition"]["id"] == environment_field.json()["id"] for row in second)


def test_group_permissions_are_unioned_and_removed_with_membership() -> None:
    headers = auth("admin@example.com", "Admin123!")
    environment = it_environment(headers)
    requester = next(
        row
        for row in client.get("/api/users", headers=headers).json()
        if row["email"] == "requester@example.com"
    )
    group = client.post(
        "/api/groups",
        headers=headers,
        json={"name": "Permission Test Group", "description": "Test", "is_active": True},
    ).json()
    assert (
        client.post(
            f"/api/groups/{group['id']}/members", headers=headers, json={"user_id": requester["id"]}
        ).status_code
        == 201
    )
    assigned = client.post("/api/access/bulk", headers=headers, json={
        "subject_type": "groups", "subject_ids": [group["id"]],
        "environment_id": environment["id"], "levels": {"cases_assign": "edit"},
    })
    assert assigned.status_code == 200
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "requester@example.com"))
        assert user and "case.assign" in permissions(db, user, uuid.UUID(environment["id"]))
    assert (
        client.delete(f"/api/groups/{group['id']}/members/{requester['id']}", headers=headers).status_code
        == 204
    )
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "requester@example.com"))
        assert user and "case.assign" not in permissions(db, user, uuid.UUID(environment["id"]))


def test_participant_access_public_comments_and_manager_isolation() -> None:
    admin_headers = auth("admin@example.com", "Admin123!")
    participant = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "display_name": "Case Participant",
            "email": "participant@example.com",
            "password": "Participant123!",
            "is_active": True,
            "is_system_admin": False,
        },
    ).json()
    outsider = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "display_name": "Case Outsider",
            "email": "outsider@example.com",
            "password": "Outsider123!",
            "is_active": True,
            "is_system_admin": False,
        },
    ).json()
    requester_headers = auth("requester@example.com", "Requester123!")
    participant_headers = auth("participant@example.com", "Participant123!")
    outsider_headers = auth("outsider@example.com", "Outsider123!")
    environment = it_environment(admin_headers)
    requester = next(row for row in client.get("/api/users", headers=admin_headers).json() if row["email"] == "requester@example.com")
    assert client.post("/api/access/bulk", headers=admin_headers, json={
        "subject_type": "users", "subject_ids": [requester["id"]],
        "environment_id": environment["id"], "levels": {"cases_create": "edit", "cases_view": "view"},
    }).status_code == 200
    case = create_case(requester_headers, [participant["id"]])
    assert client.get(f"/api/cases/{case['id']}", headers=requester_headers).status_code == 200
    assert client.get(f"/api/cases/{case['id']}", headers=participant_headers).status_code == 200
    assert client.get(f"/api/cases/{case['id']}", headers=outsider_headers).status_code == 403
    assert (
        client.post(
            f"/api/cases/{case['id']}/public-comments",
            headers=participant_headers,
            json={"body": "Participant public reply"},
        ).status_code
        == 201
    )
    assert (
        client.get(f"/api/cases/{case['id']}/manager-comments", headers=participant_headers).status_code
        == 403
    )
    assert (
        client.get(
            f"/api/cases/{case['id']}/manager-comments", headers=auth("agent@example.com", "Agent123!")
        ).status_code
        == 403
    )
    envadmin_headers = auth("envadmin@example.com", "EnvAdmin123!")
    assert (
        client.post(
            f"/api/cases/{case['id']}/manager-comments",
            headers=envadmin_headers,
            json={"body": "Environment manager only"},
        ).status_code
        == 201
    )
    assert (
        client.get(f"/api/cases/{case['id']}/manager-comments", headers=envadmin_headers).status_code == 200
    )
    assert client.get(f"/api/cases/{case['id']}/manager-comments", headers=admin_headers).status_code == 200
    assert outsider["email"] == "outsider@example.com"


def test_environment_field_catalog_boundaries() -> None:
    admin_headers = auth("admin@example.com", "Admin123!")
    envadmin_headers = auth("envadmin@example.com", "EnvAdmin123!")
    environment = it_environment(envadmin_headers)
    field = client.post(
        "/api/user-fields",
        headers=admin_headers,
        json={
            "key": "employee_number",
            "label_he": "מספר עובד",
            "label_en": "Employee number",
            "field_type": "short_text",
            "is_required": False,
            "is_active": True,
            "options_json": [],
            "default_value_json": None,
            "validation_json": {},
            "sort_order": 1,
        },
    ).json()
    selected = client.put(
        f"/api/environments/{environment['id']}/user-fields",
        headers=envadmin_headers,
        json=[
            {
                "user_field_definition_id": field["id"],
                "is_visible": True,
                "is_required": True,
                "is_editable_by_user": True,
                "is_editable_by_environment_admin": True,
                "sort_order": 1,
            }
        ],
    )
    assert selected.status_code == 200
    assert (
        client.post(
            "/api/user-fields",
            headers=envadmin_headers,
            json={
                "key": "forbidden_global",
                "label_he": "אסור",
                "label_en": "Forbidden",
                "field_type": "short_text",
            },
        ).status_code
        == 403
    )


def test_sub_priority_parent_and_required_core_fields() -> None:
    headers = auth("admin@example.com", "Admin123!")
    environment = it_environment(headers)
    priorities = client.get(f"/api/environments/{environment['id']}/priorities", headers=headers).json()
    high = next(row for row in priorities if row["code"] == "high")
    normal = next(row for row in priorities if row["code"] == "normal")
    assert all(row["priority_id"] == high["id"] for row in high["sub_priorities"])
    request_type = client.get(
        f"/api/request-types?environment_id={environment['id']}", headers=headers
    ).json()[0]
    missing_core = client.post(
        "/api/cases",
        headers=headers,
        json={
            "environment_id": environment["id"],
            "request_type_id": request_type["id"],
            "title": "Missing",
            "values": [],
        },
    )
    assert missing_core.status_code == 422
    mismatched = client.post(
        "/api/cases",
        headers=headers,
        json={
            "environment_id": environment["id"],
            "request_type_id": request_type["id"],
            "title": "Mismatched priority",
            "description": "Core description",
            "priority_id": normal["id"],
            "sub_priority_id": high["sub_priorities"][0]["id"],
            "values": [],
        },
    )
    assert mismatched.status_code == 422


def option(label: str, order: int) -> dict:
    return {
        "value": f"option-{order}",
        "label_he": label,
        "label_en": "",
        "is_active": True,
        "sort_order": order,
    }


def field_payload(
    key: str,
    field_type: str = "short_text",
    options: list[dict] | None = None,
    environment_ids: list[str] | None = None,
) -> dict:
    return {
        "key": key,
        "label_he": "שדה בדיקה",
        "label_en": "",
        "field_type": field_type,
        "is_required": False,
        "is_active": True,
        "options_json": options or [],
        "default_value_json": None,
        "validation_json": {},
        "sort_order": 1,
        "environment_ids": environment_ids or [],
    }


def test_group_validation_trim_and_duplicate_name() -> None:
    headers = auth("admin@example.com", "Admin123!")
    created = client.post(
        "/api/groups",
        headers=headers,
        json={"name": "  קבוצת בדיקות  ", "description": "  תיאור  ", "is_active": True},
    )
    assert created.status_code == 201
    assert created.json()["name"] == "קבוצת בדיקות" and created.json()["description"] == "תיאור"
    assert (
        client.post(
            "/api/groups", headers=headers, json={"name": " ", "description": "", "is_active": True}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/groups", headers=headers, json={"name": "א", "description": "", "is_active": True}
        ).status_code
        == 422
    )
    duplicate = client.post(
        "/api/groups", headers=headers, json={"name": "קבוצת בדיקות", "description": "", "is_active": True}
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "כבר קיימת קבוצת משתמשים בשם זה"


def test_user_field_types_options_and_key_validation() -> None:
    headers = auth("admin@example.com", "Admin123!")
    assert (
        client.post("/api/user-fields", headers=headers, json=field_payload("employee_code_test")).status_code
        == 201
    )
    single = client.post(
        "/api/user-fields",
        headers=headers,
        json=field_payload("department_test", "single_select", [option("כספים", 1)]),
    )
    assert single.status_code == 201 and len(single.json()["options_json"]) == 1
    multi = client.post(
        "/api/user-fields",
        headers=headers,
        json=field_payload("equipment_test", "multi_select", [option("מחשב", 1), option("מסך", 2)]),
    )
    assert multi.status_code == 201 and len(multi.json()["options_json"]) == 2
    assert (
        client.post(
            "/api/user-fields",
            headers=headers,
            json=field_payload("bad_multi_test", "multi_select", [option("מחשב", 1)]),
        ).status_code
        == 422
    )
    assert client.post("/api/user-fields", headers=headers, json=field_payload("1invalid")).status_code == 422


def test_user_field_environment_assignment_deduplication_and_rollback() -> None:
    headers = auth("admin@example.com", "Admin123!")
    environments = client.get("/api/environments", headers=headers).json()
    if len(environments) < 2:
        environments.append(
            client.post(
                "/api/environments",
                headers=headers,
                json={
                    "code": "FIELD_TEST",
                    "name_he": "סביבת שדות",
                    "name_en": "Field Test",
                    "description": "Test",
                },
            ).json()
        )
    ids = [environments[0]["id"], environments[1]["id"]]
    assigned = client.post(
        "/api/user-fields",
        headers=headers,
        json=field_payload("multi_environment_test", environment_ids=ids + [ids[0]]),
    )
    assert assigned.status_code == 201 and set(assigned.json()["environment_ids"]) == set(ids)
    invalid_id = "00000000-0000-0000-0000-000000000099"
    failed = client.post(
        "/api/user-fields",
        headers=headers,
        json=field_payload("rollback_field_test", environment_ids=[ids[0], invalid_id]),
    )
    assert failed.status_code == 422
    fields = client.get("/api/user-fields", headers=headers).json()
    assert all(row["key"] != "rollback_field_test" for row in fields)
