import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database.session import SessionLocal
from app.main import app
from app.modules.models import (
    Case,
    CaseFieldValue,
    CaseParticipant,
    CaseTransferHistory,
    Environment,
    FieldDefinition,
    FormDefinition,
    FormStatus,
    GlobalCaseFieldDefinition,
    GlobalCaseFieldValue,
    GlobalSubPriorityDefinition,
    PriorityDefinition,
    RequestType,
    SubPriorityDefinition,
    User,
)
from app.modules.operations.models import SlaPolicy, WorkflowDefinition, WorkflowStatus

client = TestClient(app)


def headers(email: str = "admin@example.com", password: str = "Admin123!") -> dict[str, str]:
    token = client.post("/api/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def transfer_fixture() -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.email == "admin@example.com"))
        assert admin
        source = db.scalar(select(Environment))
        assert source
        source_type = db.scalar(select(RequestType).where(RequestType.environment_id == source.id))
        assert source_type
        source_priority = db.scalar(
            select(PriorityDefinition).where(PriorityDefinition.environment_id == source.id)
        )
        assert source_priority
        source_sub_priority=db.scalar(select(SubPriorityDefinition).where(
            SubPriorityDefinition.environment_id==source.id))
        if not source_sub_priority:
            source_sub_priority = SubPriorityDefinition(
                system_number=f"SUB-{uuid.uuid4().hex[:8]}",
                environment_id=source.id,
                priority_id=source_priority.id,
                code=f"source-sub-{uuid.uuid4().hex[:6]}",
                label_he="תת־עדיפות מקור",
                is_active=True,
                sort_order=0,
            )
            db.add(source_sub_priority)
            db.flush()
            db.add(GlobalSubPriorityDefinition(
                id=source_sub_priority.id,
                code=f"source_sub_{uuid.uuid4().hex[:8]}",
                label_he=source_sub_priority.label_he,
                is_active=True,
                sort_order=0,
            ))
            db.flush()
        source_status = db.scalar(
            select(WorkflowStatus)
            .join(WorkflowDefinition)
            .where(WorkflowDefinition.environment_id == source.id, WorkflowStatus.is_initial.is_(True))
        )
        assert source_status
        target = Environment(
            code=f"TARGET-{uuid.uuid4().hex[:6].upper()}", name_he="סביבת יעד", name_en="Target"
        )
        db.add(target)
        db.flush()
        workflow = WorkflowDefinition(
            system_number=f"WF-{uuid.uuid4().hex[:8]}",
            environment_id=target.id,
            name_he="תהליך יעד",
            is_active=True,
            is_default=True,
            created_by=admin.id,
        )
        db.add(workflow)
        db.flush()
        status = WorkflowStatus(
            workflow_id=workflow.id,
            code="new",
            label_he="חדש ביעד",
            sort_order=0,
            is_initial=True,
            is_active=True,
        )
        db.add(status)
        db.flush()
        request_type = RequestType(
            system_number=f"RT-{uuid.uuid4().hex[:8]}",
            environment_id=target.id,
            code="target",
            name_he="סוג יעד",
            name_en="Target",
            is_active=True,
            requires_approval=False,
            workflow_definition_id=workflow.id,
        )
        db.add(request_type)
        db.flush()
        form = FormDefinition(request_type_id=request_type.id, version=1, status=FormStatus.published)
        db.add(form)
        db.flush()
        request_type.form_version_id = form.id
        required = FieldDefinition(
            form_definition_id=form.id,
            key="target_required",
            label_he="מידע נדרש",
            label_en="Required",
            field_type="short_text",
            is_required=True,
            is_read_only=False,
            is_active=True,
            sort_order=0,
            configuration_json={},
        )
        priority = PriorityDefinition(
            system_number=f"PRI-{uuid.uuid4().hex[:8]}",
            environment_id=target.id,
            code="normal",
            label_he="רגילה",
            is_active=True,
            sort_order=0,
        )
        db.add_all([required, priority])
        db.flush()
        sub_priority = SubPriorityDefinition(
            system_number=f"SUB-{uuid.uuid4().hex[:8]}",
            environment_id=target.id,
            priority_id=priority.id,
            code="target-sub",
            label_he="תת־עדיפות יעד",
            is_active=True,
            sort_order=0,
        )
        db.add(sub_priority)
        db.flush()
        case = Case(
            case_number=f"CASE-TRANSFER-{uuid.uuid4().hex[:6]}",
            environment_id=source.id,
            request_type_id=source_type.id,
            form_definition_id=source_type.form_version_id,
            title="קריאה להעברה",
            description="בדיקה",
            priority_id=source_priority.id,
            sub_priority_id=source_sub_priority.id if source_sub_priority else None,
            reporter_id=admin.id,
            requester_id=admin.id,
            assignee_id=admin.id,
            workflow_status_id=source_status.id,
        )
        db.add(case)
        db.flush()
        source_field = FieldDefinition(
            form_definition_id=source_type.form_version_id,
            key=f"source_only_{uuid.uuid4().hex[:6]}", label_he="שדה מקור בלבד",
            label_en="Source only", field_type="short_text", is_required=False,
            is_read_only=False, is_active=True, sort_order=99, configuration_json={},
        )
        global_field = GlobalCaseFieldDefinition(
            key=f"global_transfer_{uuid.uuid4().hex[:8]}", label_he="שדה גלובלי להעברה",
            label_en="Transfer global field", field_type="single_select", is_active=True,
        )
        db.add_all([source_field, global_field])
        db.flush()
        db.add(CaseFieldValue(case_id=case.id, field_definition_id=source_field.id, value_text="ערך מקור"))
        db.add(GlobalCaseFieldValue(case_id=case.id, global_field_id=global_field.id, value_json="option-stable-id"))
        db.add(
            CaseParticipant(
                case_id=case.id, user_id=admin.id, participant_type="participant", added_by=admin.id
            )
        )
        db.add(
            SlaPolicy(
                system_number=f"SLA-{uuid.uuid4().hex[:8]}",
                environment_id=target.id,
                request_type_id=request_type.id,
                priority_id=source_priority.id,
                name_he="SLA יעד",
                response_minutes=30,
                resolution_minutes=60,
                warning_threshold_percent=80,
                is_active=True,
            )
        )
        db.commit()
        return case.id,target.id,request_type.id,source_priority.id,source_sub_priority.id,required.id


def test_transfer_is_atomic_removes_invalid_links_and_preserves_identity(
    monkeypatch:pytest.MonkeyPatch,
) -> None:
    auth = headers()
    case_id,target_id,request_type_id,priority_id,sub_priority_id,_required_id=transfer_fixture()
    monkeypatch.setattr("app.modules.global_case_values.service.initial_status",
        lambda db: (_ for _ in ()).throw(AssertionError("transfer must not read initial status")))
    preview = client.get(
        f"/api/cases/{case_id}/transfer-preview?target_environment_id={target_id}", headers=auth
    )
    assert preview.status_code == 200 and preview.json()["removed_participant_ids"]
    requirements = client.get(
        f"/api/cases/{case_id}/transfer-requirements?request_type_id={request_type_id}", headers=auth
    )
    assert requirements.status_code == 200
    assert requirements.json()["required_fields"] == []
    assert requirements.json()["field_mappings"] == []
    assert requirements.json()["global_fields_preserved"] == 1
    assert requirements.json()["priorities"]
    global_priority_id = str(priority_id)
    payload: dict[str, object] = {
        "target_environment_id": str(target_id),
        "target_request_type_id": str(request_type_id),
        "priority_id": None,
        "sub_priority_id": None,
        "new_field_values": [],
    }
    moved = client.post(f"/api/cases/{case_id}/transfer", headers=auth, json=payload)
    assert moved.status_code == 200 and moved.json()["case_id"] == str(case_id)
    with SessionLocal() as db:
        case = db.get(Case, case_id)
        assert case
        assert case.environment_id == target_id and case.request_type_id == request_type_id
        assert str(case.priority_id)==global_priority_id and str(case.sub_priority_id)==str(sub_priority_id)
        assert case.assignee_id is None
        assert case.sla_policy_id is not None
        assert db.scalar(select(CaseParticipant).where(CaseParticipant.case_id == case_id)) is None
        assert db.scalar(select(CaseFieldValue).where(CaseFieldValue.case_id == case_id)) is None
        global_value = db.scalar(select(GlobalCaseFieldValue).where(GlobalCaseFieldValue.case_id == case_id))
        assert global_value and global_value.value_json == "option-stable-id"
        history = db.scalar(select(CaseTransferHistory).where(CaseTransferHistory.case_id == case_id))
        assert history and history.removed_participants and history.removed_assignee
        assert history.removed_fields_snapshot[0]["value"] == "ערך מקור"


def test_knowledge_upload_query_versioning_and_environment_isolation() -> None:
    auth = headers()
    environment = client.get("/api/environments", headers=auth).json()[0]
    uploaded = client.post(
        f"/api/environments/{environment['id']}/knowledge/documents",
        headers=auth,
        files={"file": ("policy.md", "נוהל רכש מחייב אישור מנהל לפני הזמנה.".encode(), "text/markdown")},
    )
    assert uploaded.status_code == 201 and uploaded.json()["status"] == "ready"
    document_id = uploaded.json()["id"]
    downloaded = client.get(
        f"/api/environments/{environment['id']}/knowledge/documents/{document_id}/download",
        headers=auth,
    )
    assert downloaded.status_code == 200 and downloaded.content
    reindexed = client.post(
        f"/api/environments/{environment['id']}/knowledge/documents/{document_id}/reindex",
        headers=auth,
    )
    assert reindexed.status_code == 200 and reindexed.json()["status"] == "ready"
    disabled = client.patch(
        f"/api/environments/{environment['id']}/knowledge/documents/{document_id}/active?enabled=false",
        headers=auth,
    )
    assert disabled.status_code == 200 and disabled.json()["is_active"] is False
    assert (
        client.patch(
            f"/api/environments/{environment['id']}/knowledge/documents/{document_id}/active?enabled=true",
            headers=auth,
        ).status_code
        == 200
    )
    answer = client.post(
        f"/api/environments/{environment['id']}/knowledge/query",
        headers=auth,
        json={"question": "מי מאשר הזמנה?"},
    )
    assert answer.status_code == 200 and answer.json()["sources"][0]["filename"] == "policy.md"
    replacement = client.post(
        f"/api/environments/{environment['id']}/knowledge/documents",
        headers=auth,
        files={"file": ("policy.md", "גרסה חדשה של נוהל הרכש.".encode(), "text/markdown")},
    )
    assert replacement.status_code == 201 and replacement.json()["version"] == 2
    rows = client.get(f"/api/environments/{environment['id']}/knowledge/documents", headers=auth).json()
    assert sum(1 for row in rows if row["original_filename"] == "policy.md" and row["is_active"]) == 1
    forbidden = client.post(
        f"/api/environments/{environment['id']}/knowledge/query",
        headers=headers("requester@example.com", "Requester123!"),
        json={"question": "נוהל"},
    )
    assert forbidden.status_code == 403


def test_ai_settings_never_returns_secret() -> None:
    response = client.get("/api/system/ai-settings", headers=headers())
    assert response.status_code == 200 and "api_key" not in response.json()
