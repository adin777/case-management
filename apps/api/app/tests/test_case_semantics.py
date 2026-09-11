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
    GlobalCaseFieldOption,
    GlobalCaseFieldValue,
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
        semantics=CaseSemanticFieldService(db)
        status_field=semantics.definition("case.status");priority_field=semantics.definition("case.priority")
        sub_field=semantics.definition("case.sub_priority");assert status_field and priority_field and sub_field
        status=db.scalar(select(GlobalCaseFieldOption).where(GlobalCaseFieldOption.global_field_id==status_field.id));assert status
        priority=db.scalar(select(GlobalCaseFieldOption).where(GlobalCaseFieldOption.global_field_id==priority_field.id));assert priority
        sub=db.scalar(select(GlobalCaseFieldOption).where(GlobalCaseFieldOption.global_field_id==sub_field.id))
        if not sub:
            sub=GlobalCaseFieldOption(id=uuid.uuid4(),global_field_id=sub_field.id,label_he="משני",
                label_en="Secondary",is_active=True,sort_order=0,metadata_json={})
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
        status_id,priority_id,sub_id=str(status.id),str(priority.id),str(sub.id)
        target_environment=db.scalar(select(Environment).where(Environment.id!=environment.id))
        if not target_environment:
            target_environment=Environment(code=f"T-{uuid.uuid4().hex[:6]}",name_he="סביבת יעד",
                name_en="Target",description=None,is_active=True)
            db.add(target_environment);db.flush()
        db.commit()

    auth=headers()
    workspace=client.get("/api/cases/workspace/query?activity_state=all",headers=auth).json()["items"]
    workspace_row=next(row for row in workspace if row["case_number"]==item_number)
    report=client.get(f"/api/reports/cases?case_number={item_number}",headers=auth).json()["items"][0]
    status_options=client.get(f"/api/cases/{case_id}/status-options",headers=auth).json()
    current=next(row for row in status_options if row["current"])
    assert workspace_row["status"]==report["status"]==current["label_he"]==status_label
    assert workspace_row["priority"]==report["priority"]==priority_label
    details=client.get(f"/api/cases/{case_id}",headers=auth).json()
    preview=client.get(f"/api/cases/{case_id}/transfer-preview?target_environment_id={target_environment.id}",headers=auth).json()
    assert str(details["workflow_status_id"])==workspace_row["status_option_id"]==report["status_option_id"]==current["id"]==status_id
    assert str(details["priority_id"])==workspace_row["priority_option_id"]==report["priority_option_id"]==priority_id
    assert str(details["sub_priority_id"])==workspace_row["sub_priority_option_id"]==report["sub_priority_option_id"]==sub_id
    assert preview["semantic_values"]["case.status"]=={"option_id":status_id,"label":status_label}
    assert preview["semantic_values"]["case.priority"]=={"option_id":priority_id,"label":priority_label}


def test_semantic_sync_backfills_missing_global_value_and_reports_conflict()->None:
    with SessionLocal() as db:
        admin=db.scalar(select(User).where(User.email=="admin@example.com"));assert admin
        environment=db.scalar(select(Environment).where(Environment.is_active.is_(True)));assert environment
        request_type=db.scalar(select(RequestType).where(RequestType.environment_id==environment.id));assert request_type
        field=db.scalar(select(GlobalCaseFieldDefinition).where(
            GlobalCaseFieldDefinition.semantic_binding=="case.status",
            GlobalCaseFieldDefinition.is_active.is_(True)));assert field
        status_rows=list(db.scalars(select(GlobalCaseFieldOption).where(
            GlobalCaseFieldOption.global_field_id==field.id,
            GlobalCaseFieldOption.is_active.is_(True)).limit(2)));assert len(status_rows)==2
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
        missing=service.sync_case(legacy)
        assert missing == []
        stored = db.get(GlobalCaseFieldValue, (legacy.id, field.id))
        assert stored and stored.value_json == str(status_rows[0].id)
        found=service.sync_case(conflict)
        assert found==[]
        assert conflict.workflow_status_id==status_rows[1].id
        db.flush()
        assert db.scalar(select(CaseSemanticSyncConflict).where(
            CaseSemanticSyncConflict.case_id==legacy.id)) is None


def test_every_select_value_references_an_option_of_its_field_with_canonical_shape()->None:
    with SessionLocal() as db:
        fields={row.id:row for row in db.scalars(select(GlobalCaseFieldDefinition))}
        options={row.id:row for row in db.scalars(select(GlobalCaseFieldOption))}
        for value in db.scalars(select(GlobalCaseFieldValue)):
            field=fields.get(value.global_field_id);assert field
            if field.field_type not in {"single_select","multi_select"}: continue
            raw=value.value_json
            ids=raw if isinstance(raw,list) else [raw]
            assert (field.field_type=="multi_select") == isinstance(raw,list)
            for raw_id in ids:
                option=options.get(uuid.UUID(str(raw_id)))
                assert option and option.global_field_id==field.id


def test_legacy_request_type_defaults_resolve_to_canonical_global_options()->None:
    with SessionLocal() as db:
        service=CaseSemanticFieldService(db)
        request_type=db.scalar(select(RequestType));assert request_type
        priority_field=service.definition("case.priority");assert priority_field
        priority_option=db.scalar(select(GlobalCaseFieldOption).where(
            GlobalCaseFieldOption.global_field_id==priority_field.id));assert priority_option
        legacy_priority_id=uuid.uuid4()
        priority_option.metadata_json={**(priority_option.metadata_json or {}),
                                       "legacy_id":str(legacy_priority_id)}
        request_type.default_priority_id=legacy_priority_id
        db.flush()
        priority=service.option_for_config_id("case.priority",request_type.default_priority_id)
        assert priority and priority_field and priority.global_field_id==priority_field.id
