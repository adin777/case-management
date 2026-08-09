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
    restored = client.post("/api/access/bulk", headers=headers, json={"subject_type": "users", "subject_ids": [requester["id"]], "environment_id": environment["id"], "levels": {"cases_create": "edit"}})
    assert restored.status_code == 200
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
    row = next(item for item in report.json()["items"] if item["status"])
    sources = client.get(f"/api/reports/cases/value-sources?environment_id={environment['id']}", headers=headers).json()
    status = next(value for value in sources["statuses"] if value["label_he"] == row["status"])
    matching = client.get(f"/api/reports/cases?environment_id={environment['id']}&workflow_status_id={status['id']}", headers=headers).json()["items"]
    assert any(value["case_number"] == row["case_number"] for value in matching)
    other = next((value for value in sources["statuses"] if value["id"] != status["id"]), None)
    if other:
        excluded = client.get(f"/api/reports/cases?environment_id={environment['id']}&workflow_status_id={other['id']}", headers=headers).json()["items"]
        assert all(value["case_number"] != row["case_number"] for value in excluded)
    descending = client.get(f"/api/reports/cases?environment_id={environment['id']}&sort=case_number&direction=desc&page_size=200", headers=headers).json()["items"]
    assert [value["case_number"] for value in descending] == sorted((value["case_number"] for value in descending), reverse=True)
    exported = client.get(f"/api/reports/cases/export?environment_id={environment['id']}", headers=headers)
    assert exported.status_code == 200
    with zipfile.ZipFile(io.BytesIO(exported.content)) as workbook:
        assert {"xl/worksheets/sheet1.xml", "xl/worksheets/sheet2.xml"}.issubset(workbook.namelist())


def test_two_step_approval_flow() -> None:
    headers = auth(); environment, request_type, _ = context(headers)
    enabled = client.patch(
        f"/api/request-types/{request_type['id']}", headers=headers, json={"requires_approval": True}
    )
    assert enabled.status_code == 200
    users = client.get("/api/users", headers=headers).json()
    agent = next(row for row in users if row["email"] == "agent@example.com")
    envadmin = next(row for row in users if row["email"] == "envadmin@example.com")
    flow = client.post(f"/api/environments/{environment['id']}/approval-flows", headers=headers, json={
        "name": "אישור דו שלבי", "request_type_id": request_type["id"], "trigger_type": "case_created",
        "steps": [{"name": "אישור מטפל", "approver_user_id": agent["id"]}, {"name": "אישור מנהל", "approver_user_id": envadmin["id"]}],
    })
    assert flow.status_code == 201
    item = create_case(headers)
    pending = client.get("/api/approvals/pending-for-me", headers=auth("agent@example.com", "Agent123!"))
    assert pending.status_code == 200
    assert any(row["case_id"] == item["id"] and row["step_name"] == "אישור מטפל" for row in pending.json())
    approval = next(row for row in client.get(f"/api/cases/{item['id']}/approvals", headers=headers).json() if row["name"] == "אישור דו שלבי")
    first = approval["tasks"][0]
    assert first["approver_name"] and first["requested_at"] and first["step_order"] == 1
    assert client.post(f"/api/approval-tasks/{first['id']}/decision", headers=auth("agent@example.com", "Agent123!"), json={"decision": "approved"}).status_code == 200
    approval = next(row for row in client.get(f"/api/cases/{item['id']}/approvals", headers=headers).json() if row["name"] == "אישור דו שלבי")
    second = next(row for row in approval["tasks"] if row["status"] == "pending")
    decided = client.post(f"/api/approval-tasks/{second['id']}/decision", headers=auth("envadmin@example.com", "EnvAdmin123!"), json={"decision": "approved"})
    assert decided.json()["status"] == "approved"
    history = next(row for row in client.get(f"/api/cases/{item['id']}/approvals", headers=headers).json() if row["id"] == approval["id"])
    assert all(task["approver_name"] for task in history["tasks"])
    assert all(task["decided_at"] for task in history["tasks"] if task["decision"])


def test_assign_unassign_uses_active_environment_members() -> None:
    headers = auth(); environment, _, _ = context(headers); item = create_case(headers)
    eligible = client.get(f"/api/environments/{environment['id']}/eligible-assignees", headers=headers)
    assert eligible.status_code == 200 and eligible.json()
    candidate = eligible.json()[0]
    assigned = client.post(f"/api/cases/{item['id']}/assign", headers=headers,
        json={"assignee_id": candidate["id"], "version": item["version"]})
    assert assigned.status_code == 200 and assigned.json()["assignee_id"] == candidate["id"]
    unassigned = client.post(f"/api/cases/{item['id']}/assign", headers=headers,
        json={"assignee_id": None, "version": assigned.json()["version"]})
    assert unassigned.status_code == 200 and unassigned.json()["assignee_id"] is None


def test_bulk_permissions_for_users_and_groups() -> None:
    headers = auth(); environment, _, _ = context(headers)
    users = client.get("/api/users", headers=headers).json()
    requester = next(row for row in users if row["email"] == "requester@example.com")
    agent = next(row for row in users if row["email"] == "agent@example.com")
    added = client.post("/api/permissions/bulk/users", headers=headers, json={
        "user_ids": [requester["id"], agent["id"]], "permission_codes": ["case.assign", "case.lock"],
        "environment_id": environment["id"], "operation": "add",
    })
    assert added.status_code == 200 and added.json()["created"] == 4
    for selected in (requester, agent):
        effective = client.get(f"/api/users/{selected['id']}/effective-permissions?environment_id={environment['id']}", headers=headers).json()
        assert {"case.assign", "case.lock"}.issubset(effective["permissions"])
    removed = client.post("/api/permissions/bulk/users", headers=headers, json={
        "user_ids": [requester["id"], agent["id"]], "permission_codes": ["case.assign", "case.lock"],
        "environment_id": environment["id"], "operation": "remove",
    })
    assert removed.json()["removed"] == 4
    group = client.post("/api/groups", headers=headers, json={"name": "קבוצת הרשאות בדיקה", "description": "בדיקה"}).json()
    client.post(f"/api/groups/{group['id']}/members", headers=headers, json={"user_id": requester["id"]})
    group_added = client.post("/api/permissions/bulk/groups", headers=headers, json={
        "group_ids": [group["id"]], "permission_codes": ["case.lock"],
        "environment_id": environment["id"], "operation": "add",
    })
    assert group_added.json()["created"] == 1


def test_case_lock_blocks_edit_but_allows_public_comment() -> None:
    admin_headers = auth(); item = create_case(admin_headers)
    assigned = client.post(f"/api/cases/{item['id']}/assign", headers=admin_headers, json={
        "assignee_id": next(row for row in client.get('/api/users', headers=admin_headers).json() if row['email'] == 'agent@example.com')["id"],
        "version": item["version"],
    }).json()
    locked = client.post(f"/api/cases/{item['id']}/lock", headers=admin_headers, json={
        "locked": True, "reason": "הקריאה בבדיקת מנהל", "version": assigned["version"],
    })
    assert locked.status_code == 200 and locked.json()["is_locked"] is True
    agent_headers = auth("agent@example.com", "Agent123!")
    blocked = client.patch(f"/api/cases/{item['id']}", headers=agent_headers, json={
        "title": "עריכה אסורה", "version": locked.json()["version"],
    })
    assert blocked.status_code == 403
    assert client.post(f"/api/cases/{item['id']}/lock", headers=agent_headers, json={
        "locked": False, "version": locked.json()["version"],
    }).status_code == 403
    comment = client.post(f"/api/cases/{item['id']}/public-comments", headers=agent_headers, json={"body": "תגובה מותרת"})
    assert comment.status_code == 201
    unlocked = client.post(f"/api/cases/{item['id']}/lock", headers=admin_headers, json={
        "locked": False, "version": locked.json()["version"],
    })
    assert unlocked.status_code == 200 and unlocked.json()["is_locked"] is False


def test_participant_add_remove_and_locked_case_permissions() -> None:
    admin = auth(); item = create_case(admin)
    users = client.get("/api/users", headers=admin).json()
    participant = next(row for row in users if row["email"] == "requester@example.com")
    added = client.post(f"/api/cases/{item['id']}/participants", headers=admin, json={"user_id": participant["id"]})
    assert added.status_code == 201
    removed = client.delete(f"/api/cases/{item['id']}/participants/{participant['id']}", headers=admin)
    assert removed.status_code == 204
    unauthorized = auth("requester@example.com", "Requester123!")
    assert client.post(f"/api/cases/{item['id']}/participants", headers=unauthorized, json={"user_id": participant["id"]}).status_code == 403
    assert client.delete(f"/api/cases/{item['id']}/participants/{participant['id']}", headers=unauthorized).status_code == 403


def test_report_filters_creator_assignee_and_updated_date() -> None:
    headers = auth(); item = create_case(headers)
    users = client.get("/api/users", headers=headers).json()
    admin = next(row for row in users if row["email"] == "admin@example.com")
    report = client.get(
        f"/api/reports/cases?created_by_id={admin['id']}&updated_from=2020-01-01T00:00:00&case_number={item['case_number']}",
        headers=headers,
    )
    assert report.status_code == 200
    assert any(row["case_number"] == item["case_number"] for row in report.json()["items"])
