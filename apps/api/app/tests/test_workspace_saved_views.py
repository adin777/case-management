from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def admin_headers() -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "Admin123!"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_case(headers: dict[str, str]) -> dict:
    environment = next(row for row in client.get("/api/environments", headers=headers).json() if row["code"] == "IT")
    request_type = client.get(f"/api/request-types?environment_id={environment['id']}", headers=headers).json()[0]
    priority = client.get(f"/api/environments/{environment['id']}/priorities", headers=headers).json()[0]
    form = client.get(f"/api/forms/{request_type['form_version_id']}", headers=headers).json()
    values = [{"field_definition_id": field["id"], "value": "bulk"} for field in form["fields"]]
    response = client.post("/api/cases", headers=headers, json={"environment_id":environment["id"],
        "request_type_id":request_type["id"],"title":"Bulk workspace case","description":"bulk",
        "priority_id":priority["id"],"values":values})
    assert response.status_code == 201, response.text
    return response.json()


def test_saved_view_crud_duplicate_default_and_owner_validation() -> None:
    headers = admin_headers()
    payload = {"name": "קריאות דחופות", "filters": {"activity_state": "active", "search": "חשוב"},
               "sort": "updated_at:desc", "visible_columns": ["case_number", "title", "status"],
               "page_size": 25, "is_default": False}
    created = client.post("/api/workspace/views", headers=headers, json=payload)
    assert created.status_code == 201
    view = created.json()
    assert view["filters"] == payload["filters"] and view["visible_columns"] == payload["visible_columns"]

    updated = client.put(f"/api/workspace/views/{view['id']}", headers=headers,
                         json={**payload, "name": "קריאות פעילות", "page_size": 50})
    assert updated.status_code == 200 and updated.json()["page_size"] == 50
    copied = client.post(f"/api/workspace/views/{view['id']}/duplicate", headers=headers)
    assert copied.status_code == 201 and copied.json()["id"] != view["id"]
    defaulted = client.post(f"/api/workspace/views/{copied.json()['id']}/default", headers=headers)
    assert defaulted.status_code == 200 and defaulted.json()["is_default"] is True
    rows = client.get("/api/workspace/views", headers=headers).json()
    assert len(rows) == 2 and sum(row["is_default"] for row in rows) == 1
    assert client.delete(f"/api/workspace/views/{view['id']}", headers=headers).status_code == 204
    assert len(client.get("/api/workspace/views", headers=headers).json()) == 1


def test_saved_view_rejects_unsupported_sort_and_columns() -> None:
    headers = admin_headers()
    invalid = client.post("/api/workspace/views", headers=headers, json={"name":"לא תקין",
        "sort":"drop:table", "visible_columns":["secret_column"], "page_size":25})
    assert invalid.status_code == 422


def test_bulk_preview_apply_exact_snapshot_and_idempotency() -> None:
    headers=admin_headers();first=create_case(headers);second=create_case(headers)
    status=client.get(f"/api/cases/{first['id']}/allowed-transitions",headers=headers).json()[0]
    preview=client.post("/api/workspace/bulk/preview",headers=headers,json={"case_ids":[first["id"],second["id"]],"action":"status","target_id":status["id"]})
    assert preview.status_code==201 and preview.json()["eligible"]==2
    applied=client.post("/api/workspace/bulk/apply",headers=headers,json={"preview_id":preview.json()["preview_id"]})
    assert applied.status_code==200 and applied.json()["succeeded"]==2 and applied.json()["failed"]==0
    assert client.get(f"/api/cases/{first['id']}",headers=headers).json()["workflow_status_id"]==status["id"]
    assert client.post("/api/workspace/bulk/apply",headers=headers,json={"preview_id":preview.json()["preview_id"]}).status_code==409
