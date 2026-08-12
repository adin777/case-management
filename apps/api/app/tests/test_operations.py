from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database.session import SessionLocal
from app.main import app
from app.modules.models import Case, Environment, FormDefinition, PriorityDefinition, RequestType, User
from app.modules.operations.models import WorkflowDefinition, WorkflowStatus, WorkflowTransition

client = TestClient(app)


def headers(email: str = "admin@example.com", password: str = "Admin123!") -> dict[str, str]:
    token = client.post("/api/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_workflow_crud_and_sla_specificity() -> None:
    auth = headers()
    environment = next(
        item for item in client.get("/api/environments", headers=auth).json() if item["code"] == "IT"
    )
    created = client.post(
        f"/api/environments/{environment['id']}/workflows",
        headers=auth,
        json={"name_he": "תהליך בדיקה", "is_default": False},
    )
    assert created.status_code == 201
    workflow = created.json()
    updated = client.patch(
        f"/api/workflows/{workflow['id']}",
        headers=auth,
        json={"name_he": "תהליך בדיקה מעודכן", "is_default": False},
    )
    assert updated.status_code == 200 and updated.json()["name_he"].endswith("מעודכן")
    request_type = client.get(f"/api/request-types?environment_id={environment['id']}", headers=auth).json()[
        0
    ]
    priority = client.get(f"/api/environments/{environment['id']}/priorities", headers=auth).json()[0]
    response = client.post(
        f"/api/environments/{environment['id']}/sla-policies",
        headers=auth,
        json={
            "name_he": "בדיקת SLA",
            "request_type_id": request_type["id"],
            "priority_id": priority["id"],
            "response_minutes": 30,
            "resolution_minutes": 240,
        },
    )
    assert response.status_code == 201 and response.json()["warning_threshold_percent"] == 80


def test_valid_and_invalid_workflow_transition_and_notification() -> None:
    auth = headers()
    with SessionLocal() as db:
        workflow = db.scalar(select(WorkflowDefinition).where(WorkflowDefinition.is_default.is_(True)))
        assert workflow is not None
        states = list(
            db.scalars(
                select(WorkflowStatus)
                .where(WorkflowStatus.workflow_id == workflow.id)
                .order_by(WorkflowStatus.sort_order)
            )
        )
        transition = db.scalar(
            select(WorkflowTransition).where(
                WorkflowTransition.from_status_id == states[0].id,
                WorkflowTransition.to_status_id == states[1].id,
            )
        )
        env = db.scalar(select(Environment))
        assert env is not None
        request_type = db.scalar(select(RequestType).where(RequestType.environment_id == env.id))
        assert request_type is not None
        priority = db.scalar(select(PriorityDefinition).where(PriorityDefinition.environment_id == env.id))
        assert priority is not None
        form = db.get(FormDefinition, request_type.form_version_id)
        assert form is not None
        admin = db.scalar(select(User).where(User.email == "admin@example.com"))
        assert admin is not None
        item = Case(
            case_number="CASE-TEST-WORKFLOW",
            environment_id=env.id,
            request_type_id=request_type.id,
            form_definition_id=form.id,
            title="בדיקת מעבר",
            description="בדיקה",
            priority_id=priority.id,
            reporter_id=admin.id,
            requester_id=admin.id,
            workflow_status_id=states[0].id,
        )
        db.add(item)
        db.commit()
        assert transition is not None
        case_id, transition_id = item.id, transition.id
    legal = client.post(f"/api/cases/{case_id}/workflow-transitions/{transition_id}", headers=auth, json={})
    assert legal.status_code == 200
    illegal = client.post(f"/api/cases/{case_id}/workflow-transitions/{transition_id}", headers=auth, json={})
    assert illegal.status_code == 409
    notification_page = client.get("/api/notifications", headers=auth).json()
    assert notification_page["unread"] >= 1


def test_attachment_guards_download_and_logical_delete() -> None:
    auth = headers()
    with SessionLocal() as db:
        case_id = db.scalar(select(Case.id).order_by(Case.created_at.desc()))
    traversal = client.post(
        f"/api/cases/{case_id}/attachments",
        headers=auth,
        files={"file": ("../secret.txt", b"no", "text/plain")},
    )
    assert traversal.status_code == 422
    uploaded = client.post(
        f"/api/cases/{case_id}/attachments",
        headers=auth,
        files={"file": ("evidence.txt", b"saved evidence", "text/plain")},
    )
    assert uploaded.status_code == 201
    attachment = uploaded.json()
    downloaded = client.get(f"/api/attachments/{attachment['id']}/download", headers=auth)
    assert downloaded.status_code == 200 and downloaded.content == b"saved evidence"
    assert client.delete(f"/api/attachments/{attachment['id']}", headers=auth).status_code == 204
    assert client.get(f"/api/attachments/{attachment['id']}/download", headers=auth).status_code == 404
    supported = [
        ("document.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("sheet.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ("slides.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
        ("archive.zip", "application/zip"),
        ("image.png", "image/png"),
    ]
    for filename, content_type in supported:
        response = client.post(
            f"/api/cases/{case_id}/attachments",
            headers=auth,
            files={"file": (filename, b"safe test payload", content_type)},
        )
        assert response.status_code == 201, (filename, response.text)
    blocked = client.post(
        f"/api/cases/{case_id}/attachments",
        headers=auth,
        files={"file": ("payload.exe", b"MZ", "application/octet-stream")},
    )
    assert blocked.status_code == 415


def test_changing_initial_status_affects_new_cases_only() -> None:
    auth = headers()
    with SessionLocal() as db:
        workflow = db.scalar(select(WorkflowDefinition).where(WorkflowDefinition.is_default.is_(True)))
        assert workflow is not None
        statuses = list(
            db.scalars(
                select(WorkflowStatus)
                .where(
                    WorkflowStatus.workflow_id == workflow.id,
                    WorkflowStatus.is_active.is_(True),
                )
                .order_by(WorkflowStatus.sort_order)
            )
        )
        assert len(statuses) >= 2
        previous = next(item for item in statuses if item.is_initial)
        replacement = next(item for item in statuses if not item.is_initial)
        existing_case = db.scalar(select(Case).where(Case.workflow_status_id == previous.id))
        existing_case_id = existing_case.id if existing_case else None
    changed = client.post(f"/api/workflow-statuses/{replacement.id}/set-initial", headers=auth)
    assert changed.status_code == 200 and changed.json()["is_initial"] is True
    with SessionLocal() as db:
        previous_stored = db.get(WorkflowStatus, previous.id)
        replacement_stored = db.get(WorkflowStatus, replacement.id)
        assert previous_stored is not None and previous_stored.is_initial is False
        assert replacement_stored is not None and replacement_stored.is_initial is True
        if existing_case_id:
            existing_stored = db.get(Case, existing_case_id)
            assert existing_stored is not None and existing_stored.workflow_status_id == previous.id
    client.post(f"/api/workflow-statuses/{previous.id}/set-initial", headers=auth)


def test_system_field_reorder_is_environment_scoped() -> None:
    auth = headers()
    environments = client.get("/api/environments", headers=auth).json()
    environment = next(
        item
        for item in environments
        if len(client.get(f"/api/environments/{item['id']}/priorities", headers=auth).json()) >= 2
    )
    original = client.get(f"/api/environments/{environment['id']}/priorities", headers=auth).json()
    original_ids = [item["id"] for item in original]
    changed = client.put(
        f"/api/environments/{environment['id']}/system-fields/priority/reorder",
        headers=auth,
        json={"ids": list(reversed(original_ids))},
    )
    assert changed.status_code == 200
    reordered = client.get(f"/api/environments/{environment['id']}/priorities", headers=auth).json()
    assert [item["id"] for item in reordered] == list(reversed(original_ids))
    client.put(
        f"/api/environments/{environment['id']}/system-fields/priority/reorder",
        headers=auth,
        json={"ids": original_ids},
    )


def test_all_system_field_orders_persist_and_duplicate_ids_are_rejected() -> None:
    auth = headers()
    environment = next(
        item for item in client.get("/api/environments", headers=auth).json() if item["code"] == "IT"
    )
    for field_code in ("status", "request_type", "priority", "sub_priority"):
        fields = client.get(f"/api/environments/{environment['id']}/system-fields", headers=auth).json()
        options = next(field["options"] for field in fields if field["code"] == field_code)
        if len(options) < 2:
            continue
        original_ids = [option["id"] for option in options]
        reversed_ids = list(reversed(original_ids))
        changed = client.put(
            f"/api/environments/{environment['id']}/system-fields/{field_code}/reorder",
            headers=auth,
            json={"ids": reversed_ids},
        )
        assert changed.status_code == 200
        persisted = client.get(f"/api/environments/{environment['id']}/system-fields", headers=auth).json()
        assert [
            option["id"]
            for option in next(field["options"] for field in persisted if field["code"] == field_code)
        ] == reversed_ids
        duplicate = client.put(
            f"/api/environments/{environment['id']}/system-fields/{field_code}/reorder",
            headers=auth,
            json={"ids": [original_ids[0]] * len(original_ids)},
        )
        assert duplicate.status_code == 422
        client.put(
            f"/api/environments/{environment['id']}/system-fields/{field_code}/reorder",
            headers=auth,
            json={"ids": original_ids},
        )
