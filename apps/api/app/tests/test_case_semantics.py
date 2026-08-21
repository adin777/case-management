import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database.session import SessionLocal
from app.main import app
from app.modules.case_semantics.service import CaseSemanticFieldService
from app.modules.models import (
    Case,
    CaseSemanticSyncConflict,
    Environment,
    GlobalCaseFieldDefinition,
    GlobalCaseFieldValue,
    GlobalPriorityDefinition,
    GlobalStatusDefinition,
    GlobalSubPriorityDefinition,
    RequestType,
    User,
)

client=TestClient(app)


def headers()->dict[str,str]:
    token=client.post("/api/auth/login",json={"email":"admin@example.com","password":"Admin123!"}).json()["access_token"]
    return {"Authorization":f"Bearer {token}"}


def test_semantic_global_fields_sync_and_all_read_consumers_agree()->None:
    with SessionLocal() as db:
        admin=db.scalar(select(User).where(User.email=="admin@example.com"));assert admin
        environment=db.scalar(select(Environment).where(Environment.is_active.is_(True)));assert environment
        request_type=db.scalar(select(RequestType).where(RequestType.environment_id==environment.id));assert request_type
        status=db.scalar(select(GlobalStatusDefinition).where(GlobalStatusDefinition.is_active.is_(True)));assert status
        priority=db.scalar(select(GlobalPriorityDefinition).where(GlobalPriorityDefinition.is_active.is_(True)));assert priority
        sub=db.scalar(select(GlobalSubPriorityDefinition).where(GlobalSubPriorityDefinition.is_active.is_(True)))
        if not sub:
            sub=GlobalSubPriorityDefinition(code=f"semantic_{uuid.uuid4().hex}",label_he="משני",
                label_en="Secondary",is_active=True,sort_order=0)
            db.add(sub);db.flush()
        definitions={}
        for binding in ("case.status","case.priority","case.sub_priority"):
            existing=db.scalar(select(GlobalCaseFieldDefinition).where(
                GlobalCaseFieldDefinition.semantic_binding==binding,
                GlobalCaseFieldDefinition.is_active.is_(True)))
            if existing:
                definitions[binding]=existing;continue
            row=GlobalCaseFieldDefinition(key=f"semantic_{uuid.uuid4().hex}",label_he=binding,
                label_en=binding,field_type="single_select",is_required=False,is_active=True,
                sort_order=0,configuration_json={"options":[]},semantic_binding=binding)
            db.add(row);db.flush();definitions[binding]=row
        item=Case(case_number=f"CASE-SEM-{uuid.uuid4().hex[:8]}",environment_id=environment.id,
            request_type_id=request_type.id,form_definition_id=request_type.form_version_id,
            title="Semantic consumer agreement",description="regression",reporter_id=admin.id,
            requester_id=admin.id,workflow_status_id=None,priority_id=None,sub_priority_id=None)
        db.add(item);db.flush()
        db.add_all([
            GlobalCaseFieldValue(case_id=item.id,global_field_id=definitions["case.status"].id,value_json=str(status.id)),
            GlobalCaseFieldValue(case_id=item.id,global_field_id=definitions["case.priority"].id,value_json=str(priority.id)),
            GlobalCaseFieldValue(case_id=item.id,global_field_id=definitions["case.sub_priority"].id,value_json=str(sub.id)),
        ])
        db.flush();conflicts=CaseSemanticFieldService(db).sync_case(item)
        assert conflicts==[]
        assert item.workflow_status_id==status.id and item.priority_id==priority.id and item.sub_priority_id==sub.id
        case_id,item_number=item.id,item.case_number
        status_label,priority_label=status.label_he,priority.label_he
        db.commit()

    auth=headers()
    workspace=client.get("/api/cases/workspace/query?activity_state=all",headers=auth).json()["items"]
    workspace_row=next(row for row in workspace if row["case_number"]==item_number)
    report=client.get(f"/api/reports/cases?case_number={item_number}",headers=auth).json()["items"][0]
    status_options=client.get(f"/api/cases/{case_id}/status-options",headers=auth).json()
    current=next(row for row in status_options if row["current"])
    assert workspace_row["status"]==report["status"]==current["label_he"]==status_label
    assert workspace_row["priority"]==report["priority"]==priority_label


def test_semantic_sync_backfills_missing_global_value_and_reports_conflict()->None:
    with SessionLocal() as db:
        admin=db.scalar(select(User).where(User.email=="admin@example.com"));assert admin
        environment=db.scalar(select(Environment).where(Environment.is_active.is_(True)));assert environment
        request_type=db.scalar(select(RequestType).where(RequestType.environment_id==environment.id));assert request_type
        status_rows=list(db.scalars(select(GlobalStatusDefinition).where(
            GlobalStatusDefinition.is_active.is_(True)).limit(2)));assert len(status_rows)==2
        field=db.scalar(select(GlobalCaseFieldDefinition).where(
            GlobalCaseFieldDefinition.semantic_binding=="case.status",
            GlobalCaseFieldDefinition.is_active.is_(True)));assert field
        legacy=Case(case_number=f"CASE-SEM-{uuid.uuid4().hex[:8]}",environment_id=environment.id,
            request_type_id=request_type.id,title="Legacy backfill",reporter_id=admin.id,
            requester_id=admin.id,workflow_status_id=status_rows[0].id)
        conflict=Case(case_number=f"CASE-SEM-{uuid.uuid4().hex[:8]}",environment_id=environment.id,
            request_type_id=request_type.id,title="Conflict report",reporter_id=admin.id,
            requester_id=admin.id,workflow_status_id=status_rows[0].id)
        db.add_all([legacy,conflict]);db.flush()
        db.add(GlobalCaseFieldValue(case_id=conflict.id,global_field_id=field.id,
            value_json=str(status_rows[1].id)));db.flush()
        service=CaseSemanticFieldService(db)
        assert service.sync_case(legacy)==[]
        stored = db.get(GlobalCaseFieldValue, (legacy.id, field.id))
        assert stored is not None
        assert stored.value_json == str(status_rows[0].id)
        found=service.sync_case(conflict)
        assert len(found)==1 and found[0].reason=="value_mismatch"
        assert conflict.workflow_status_id==status_rows[0].id
        db.flush()
        assert db.scalar(select(CaseSemanticSyncConflict).where(
            CaseSemanticSyncConflict.case_id==conflict.id)) is not None
