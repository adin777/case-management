import io
import zipfile

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth(email: str = "admin@example.com", password: str = "Admin123!") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def context(headers: dict[str, str]) -> tuple[dict, dict, dict]:
    environment = next(row for row in client.get("/api/environments", headers=headers).json() if row["code"] == "IT")
    request_type = client.get(f"/api/request-types?environment_id={environment['id']}", headers=headers).json()[0]
    priority = client.get(f"/api/environments/{environment['id']}/priorities", headers=headers).json()[0]
    return environment, request_type, priority


def create_case(headers: dict[str, str]) -> dict:
    environment, request_type, priority = context(headers)
    form = client.get(f"/api/forms/{request_type['form_version_id']}", headers=headers).json()
    values = [{"field_definition_id": field["id"], "value": "test"} for field in form["fields"]]
    response = client.post("/api/cases", headers=headers, json={
        "environment_id": environment["id"], "request_type_id": request_type["id"],
        "title": "Configurable platform test", "description": "Platform test case",
        "priority_id": priority["id"], "values": values,
    })
    assert response.status_code == 201, response.text
    return response.json()


def test_numbering_and_case_field_options() -> None:
    headers = auth(); environment, _, _ = context(headers)
    first = client.post("/api/request-types", headers=headers, json={"environment_id": environment["id"], "code": "number_test_a", "name_he": "מספור א", "name_en": "A"})
    second = client.post("/api/request-types", headers=headers, json={"environment_id": environment["id"], "code": "number_test_b", "name_he": "מספור ב", "name_en": "B"})
    assert first.status_code == second.status_code == 201
    assert first.json()["form_version_id"]
    assert first.json()["system_number"] != second.json()["system_number"]
    first_number = int(first.json()["system_number"].split("-")[-1])
    second_number = int(second.json()["system_number"].split("-")[-1])
    assert second_number == first_number + 1
    field = client.post(f"/api/environments/{environment['id']}/case-fields", headers=headers, json={
        "key": "requested_system_test", "label_he": "מערכת מבוקשת", "field_type": "single_select",
        "options_json": [{"value": "sap", "label_he": "SAP", "sort_order": 1}],
    })
    assert field.status_code == 201 and field.json()["system_number"].startswith("CF-")
    assert field.json()["options_json"][0]["label_he"] == "SAP"


def test_direct_permission_deny_overrides_role() -> None:
    headers = auth(); environment, _, _ = context(headers)
    requester = next(row for row in client.get("/api/users", headers=headers).json() if row["email"] == "requester@example.com")
    before = client.get(f"/api/users/{requester['id']}/effective-permissions?environment_id={environment['id']}", headers=headers).json()["permissions"]
    assert "case.create" in before
    assigned = client.post(f"/api/users/{requester['id']}/direct-permissions", headers=headers, json={"permission_code": "case.create", "environment_id": environment["id"], "is_allowed": False})
    assert assigned.status_code == 201
    after = client.get(f"/api/users/{requester['id']}/effective-permissions?environment_id={environment['id']}", headers=headers).json()["permissions"]
    assert "case.create" not in after
    removed = client.delete(f"/api/users/{requester['id']}/direct-permissions/{assigned.json()['id']}", headers=headers)
    assert removed.status_code == 204


def test_automation_assignment_and_execution_log() -> None:
    headers = auth(); environment, request_type, _ = context(headers)
    agent = next(row for row in client.get("/api/users", headers=headers).json() if row["email"] == "agent@example.com")
    rule = client.post("/api/automation-rules", headers=headers, json={
        "environment_id": environment["id"], "name": "שיוך קריאות הרשאות",
        "trigger_type": "request_type_selected", "conditions_json": {"logic": "AND", "conditions": [{"field": "request_type_id", "operator": "equals", "value": request_type["id"]}]},
        "actions_json": [{"type": "assign_user", "value": agent["id"]}],
    })
    assert rule.status_code == 201
    item = create_case(headers)
    assert item["assignee_id"] == agent["id"]
    logs = client.get(f"/api/automation-executions?environment_id={environment['id']}", headers=headers).json()
    assert any(row["rule_id"] == rule.json()["id"] and row["matched"] for row in logs)


def test_report_filters_and_real_xlsx() -> None:
    headers = auth(); environment, request_type, _ = context(headers)
    create_case(headers)
    report = client.get(f"/api/reports/cases?environment_id={environment['id']}&request_type_id={request_type['id']}&sort=case_number&direction=asc", headers=headers)
    assert report.status_code == 200 and report.json()["total"] >= 1
    exported = client.get(f"/api/reports/cases/export?environment_id={environment['id']}", headers=headers)
    assert exported.status_code == 200
    with zipfile.ZipFile(io.BytesIO(exported.content)) as workbook:
        assert {"xl/worksheets/sheet1.xml", "xl/worksheets/sheet2.xml"}.issubset(workbook.namelist())


def test_two_step_approval_flow() -> None:
    headers = auth(); environment, request_type, _ = context(headers)
    users = client.get("/api/users", headers=headers).json()
    agent = next(row for row in users if row["email"] == "agent@example.com")
    envadmin = next(row for row in users if row["email"] == "envadmin@example.com")
    flow = client.post(f"/api/environments/{environment['id']}/approval-flows", headers=headers, json={
        "name": "אישור דו שלבי", "request_type_id": request_type["id"], "trigger_type": "case_created",
        "steps": [{"name": "אישור מטפל", "approver_user_id": agent["id"]}, {"name": "אישור מנהל", "approver_user_id": envadmin["id"]}],
    })
    assert flow.status_code == 201
    item = create_case(headers)
    approval = next(row for row in client.get(f"/api/cases/{item['id']}/approvals", headers=headers).json() if row["name"] == "אישור דו שלבי")
    first = approval["tasks"][0]
    assert client.post(f"/api/approval-tasks/{first['id']}/decision", headers=auth("agent@example.com", "Agent123!"), json={"decision": "approved"}).status_code == 200
    approval = next(row for row in client.get(f"/api/cases/{item['id']}/approvals", headers=headers).json() if row["name"] == "אישור דו שלבי")
    second = next(row for row in approval["tasks"] if row["status"] == "pending")
    decided = client.post(f"/api/approval-tasks/{second['id']}/decision", headers=auth("envadmin@example.com", "EnvAdmin123!"), json={"decision": "approved"})
    assert decided.json()["status"] == "approved"
