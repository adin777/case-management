import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database.session import SessionLocal
from app.main import app
from app.modules.case_relations import service as relation_service
from app.modules.models import Case, Environment, GlobalStatusDefinition, RequestType, User

client = TestClient(app)


def auth() -> dict[str, str]:
    token = client.post("/api/auth/login", json={"email":"admin@example.com","password":"Admin123!"}).json()["access_token"]
    return {"Authorization":f"Bearer {token}"}


def hierarchy_fixture() -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.email == "admin@example.com")); assert admin
        environments = list(db.scalars(select(Environment).where(Environment.is_active.is_(True)).limit(2)))
        if len(environments) == 1:
            second = Environment(code=f"REL-{uuid.uuid4().hex[:6]}", name_he="סביבת קשר", name_en="Relation Environment")
            db.add(second); db.flush(); environments.append(second)
            source_type = db.scalar(select(RequestType).where(RequestType.environment_id == environments[0].id)); assert source_type
            request_type = RequestType(system_number=f"RT-{uuid.uuid4().hex[:8]}", environment_id=second.id,
                code=f"relation-{uuid.uuid4().hex[:5]}", name_he="סוג קשר", name_en="Relation Type",
                is_active=True, requires_approval=False)
            db.add(request_type); db.flush()
        types = []
        for environment in environments:
            row = db.scalar(select(RequestType).where(RequestType.environment_id == environment.id))
            if not row:
                row = RequestType(system_number=f"RT-{uuid.uuid4().hex[:8]}", environment_id=environment.id,
                    code=f"relation-{uuid.uuid4().hex[:5]}", name_he="סוג קשר", name_en="Relation Type",
                    is_active=True, requires_approval=False)
                db.add(row); db.flush()
            types.append(row)
        status_rows = list(db.scalars(select(GlobalStatusDefinition).where(GlobalStatusDefinition.is_active.is_(True)).limit(2)))
        assert len(status_rows) >= 2
        cases = []
        for index, environment in enumerate((environments[0], environments[1], environments[0])):
            request_type = types[0] if environment.id == environments[0].id else types[1]
            item = Case(case_number=f"CASE-REL-{uuid.uuid4().hex[:8]}", environment_id=environment.id,
                request_type_id=request_type.id, form_definition_id=request_type.form_version_id,
                title=f"Relation case {index}", reporter_id=admin.id, requester_id=admin.id,
                workflow_status_id=status_rows[0].id)
            db.add(item); db.flush(); cases.append(item.id)
        db.commit(); return cases[0],cases[1],cases[2],status_rows[1].id


def test_cross_environment_hierarchy_cycle_protection_and_explicit_status_cascade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = auth(); parent_id, child_id, grandchild_id, target_status_id = hierarchy_fixture()
    first = client.post(f"/api/cases/{parent_id}/relations", headers=headers, json={"child_case_id":str(child_id)})
    assert first.status_code == 201
    second = client.post(f"/api/cases/{child_id}/children", headers=headers, json={"child_case_id":str(grandchild_id)})
    assert second.status_code == 201
    cycle = client.post(f"/api/cases/{grandchild_id}/relations", headers=headers, json={"child_case_id":str(parent_id)})
    assert cycle.status_code == 409 and cycle.json()["code"] == "CASE_RELATION_CYCLE"
    relations = client.get(f"/api/cases/{parent_id}/relations", headers=headers).json()
    assert relations["children"][0]["id"] == str(child_id)

    only_parent = client.post(f"/api/cases/{parent_id}/status-change-preview", headers=headers,
        json={"target_status_id":str(target_status_id),"include_descendants":False})
    assert only_parent.status_code == 200 and only_parent.json()["total_descendants"] == 0
    applied_parent = client.post(f"/api/cases/{parent_id}/status-change", headers=headers,
        json={"preview_id":only_parent.json()["preview_id"]})
    assert applied_parent.json()["updated"] == [str(parent_id)]
    with SessionLocal() as db:
        parent, child = db.get(Case,parent_id), db.get(Case,child_id)
        assert parent and child
        assert parent.workflow_status_id == target_status_id
        assert child.workflow_status_id != target_status_id

    all_cases = client.post(f"/api/cases/{parent_id}/status-change-preview", headers=headers,
        json={"target_status_id":str(target_status_id),"include_descendants":True})
    assert all_cases.status_code == 200 and all_cases.json()["total_descendants"] == 2
    applied_all = client.post(f"/api/cases/{parent_id}/status-change", headers=headers,
        json={"preview_id":all_cases.json()["preview_id"]})
    assert applied_all.json()["updated_count"] == 3
    duplicate = client.post(f"/api/cases/{parent_id}/status-change", headers=headers,
        json={"preview_id":all_cases.json()["preview_id"]})
    assert duplicate.status_code == 409

    with SessionLocal() as db:
        parent, child, grandchild = db.get(Case,parent_id), db.get(Case,child_id), db.get(Case,grandchild_id)
        assert parent and child and grandchild
        allowed_environment_id = parent.environment_id
        denied_environment_id = child.environment_id
        assert allowed_environment_id != denied_environment_id
        grandchild.is_locked = True
        db.commit()
    monkeypatch.setattr("app.modules.api.permissions", lambda db,user,environment_id:
        {"case.change_status"} if environment_id == allowed_environment_id else set())
    monkeypatch.setattr(relation_service,"can_manage_locked_case",lambda db,user,environment_id:False)
    restricted = client.post(f"/api/cases/{parent_id}/status-change-preview", headers=headers,
        json={"target_status_id":str(target_status_id),"include_descendants":True})
    assert restricted.status_code == 200
    assert restricted.json()["unauthorized"] == [str(child_id)]
    assert restricted.json()["locked"] == [str(grandchild_id)]
    restricted_apply = client.post(f"/api/cases/{parent_id}/status-change",headers=headers,
        json={"preview_id":restricted.json()["preview_id"]})
    assert restricted_apply.status_code == 200
    assert restricted_apply.json()["updated"] == [str(parent_id)]
