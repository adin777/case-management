from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth(email: str = "admin@example.com", password: str = "Admin123!") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def context(headers: dict[str, str]) -> tuple[dict, dict, dict]:
    environment = next(row for row in client.get("/api/environments", headers=headers).json() if row["code"] == "IT")
    request_type = client.get(f"/api/request-types?environment_id={environment['id']}", headers=headers).json()[0]
    form = client.get(f"/api/forms/{request_type['form_version_id']}", headers=headers).json()
    return environment, request_type, form


def test_safe_priority_and_sub_priority_deletion() -> None:
    headers = auth(); environment, request_type, form = context(headers)
    unused = client.post(f"/api/environments/{environment['id']}/priorities", headers=headers, json={"code": "unused_delete", "label_he": "למחיקה", "is_active": True})
    assert unused.status_code == 201
    assert client.delete(f"/api/priorities/{unused.json()['id']}", headers=headers).status_code == 204
    used = client.post(f"/api/environments/{environment['id']}/priorities", headers=headers, json={"code": "used_delete", "label_he": "בשימוש", "is_active": True}).json()
    sub = client.post(f"/api/environments/{environment['id']}/sub-priorities", headers=headers, json={"code": "used_sub_delete", "label_he": "תת בשימוש", "is_active": True}).json()
    values = [{"field_definition_id": field["id"], "value": "בדיקה"} for field in form["fields"]]
    created = client.post("/api/cases", headers=headers, json={"environment_id": environment["id"], "request_type_id": request_type["id"], "title": "בדיקת מחיקה בטוחה", "description": "ערכים בשימוש", "priority_id": used["id"], "sub_priority_id": sub["id"], "values": values})
    assert created.status_code == 201, created.text
    blocked_priority = client.delete(f"/api/priorities/{used['id']}", headers=headers)
    blocked_sub = client.delete(f"/api/sub-priorities/{sub['id']}", headers=headers)
    assert blocked_priority.status_code == blocked_sub.status_code == 409
    assert "לא ניתן למחוק" in blocked_priority.text and "ניתן להשבית" in blocked_sub.text


def test_inactive_environment_is_hidden_only_from_case_creation() -> None:
    headers = auth(); environment, _, _ = context(headers)
    try:
        assert client.patch(f"/api/environments/{environment['id']}", headers=headers, json={"is_active": False}).status_code == 200
        creation_ids = {row["id"] for row in client.get("/api/case-creation/environments", headers=headers).json()}
        historical_ids = {row["id"] for row in client.get("/api/environments", headers=headers).json()}
        assert environment["id"] not in creation_ids
        assert environment["id"] in historical_ids
    finally:
        client.patch(f"/api/environments/{environment['id']}", headers=headers, json={"is_active": True})


def test_workspace_query_and_environment_membership_copy() -> None:
    headers = auth(); environment, _, _ = context(headers)
    users = client.get("/api/users", headers=headers).json()
    source = next(row for row in users if row["email"] == "envadmin@example.com")
    target = next(row for row in users if row["email"] == "agent@example.com")
    original_target = [{"environment_id": row["environment_id"], "role_id": row["role_id"]} for row in target["memberships"]]
    copied = client.post("/api/users/environment-memberships/copy", headers=headers, json={"source_user_id": source["id"], "target_user_ids": [target["id"]], "mode": "replace_all"})
    assert copied.status_code == 200
    refreshed = client.get(f"/api/users/{target['id']}", headers=headers).json()
    assert {(row["environment_id"], row["role_id"]) for row in refreshed["memberships"]} == {(row["environment_id"], row["role_id"]) for row in source["memberships"]}
    assert client.put(f"/api/users/{target['id']}/environment-memberships", headers=headers, json=original_target).status_code == 200
    workspace = client.get("/api/cases/workspace/query?view=my&activity_state=all", headers=headers)
    assert workspace.status_code == 200
    assert workspace.json()["can_view_assigned_cases"] is True
    assert all("updated_at" in row for row in workspace.json()["items"])
    assert environment["id"] in {row["environment_id"] for row in source["memberships"]}
