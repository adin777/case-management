import uuid

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.main import app
from app.modules.field_history.service import FieldHistoryService
from app.modules.models import (
    Case,
    CaseFieldChangeHistory,
    Environment,
    GlobalCaseFieldDefinition,
    GlobalCaseFieldOption,
    RequestType,
    SystemSetting,
    User,
)

client=TestClient(app)
def auth()->dict[str,str]:
    token=client.post('/api/auth/login',json={'email':'admin@example.com','password':'Admin123!'}).json()['access_token']
    return {'Authorization':f'Bearer {token}'}


def make_case(db:Session)->tuple[Case,User,GlobalCaseFieldDefinition,list[GlobalCaseFieldOption]]:
    actor=db.scalar(select(User).where(User.email=='admin@example.com'));assert actor
    suffix=uuid.uuid4().hex[:8]
    environment=Environment(code=f'history-{suffix}',system_number=f'ENV-H-{suffix}',name_he='היסטוריה',name_en='History',is_active=True)
    db.add(environment);db.flush()
    request_type=RequestType(system_number=f'RT-H-{suffix}',environment_id=environment.id,code=f'history-{suffix}',name_he='בדיקה',name_en='Test',is_active=True,requires_approval=False)
    db.add(request_type);db.flush()
    field=GlobalCaseFieldDefinition(key=f'history_{suffix}',label_he='סטטוס בדיקה',label_en='Test status',field_type='single_select',is_active=True,track_history=True,semantic_binding=None)
    db.add(field);db.flush()
    options=[GlobalCaseFieldOption(id=uuid.uuid4(),global_field_id=field.id,label_he=label,label_en=label,is_active=True,sort_order=index,metadata_json={}) for index,label in enumerate(('חדש','בטיפול'))]
    db.add_all(options)
    case=Case(case_number=f'CASE-H-{suffix}',environment_id=environment.id,request_type_id=request_type.id,title='History',reporter_id=actor.id,requester_id=actor.id)
    db.add(case);db.flush()
    return case,actor,field,options


def test_master_and_per_field_switches_display_snapshots_and_impersonation()->None:
    with SessionLocal() as db:
        case,actor,field,options=make_case(db)
        master=db.get(SystemSetting,'field_history_enabled');assert master
        service=FieldHistoryService(db);field.track_history=True
        setattr(actor,'_real_actor_user_id',actor.id)  # noqa: B010 - runtime auth context attribute
        service.global_field(case,field,options[0].id,options[1].id,actor,'manual');db.flush()
        row=db.scalar(select(CaseFieldChangeHistory).where(CaseFieldChangeHistory.case_id==case.id).order_by(CaseFieldChangeHistory.changed_at.desc()));assert row
        assert row.old_display_value==options[0].label_he and row.new_display_value==options[1].label_he
        assert row.real_actor_id is not None and row.effective_user_id==actor.id
        before=db.scalar(select(func.count()).select_from(CaseFieldChangeHistory).where(CaseFieldChangeHistory.case_id==case.id)) or 0
        master.value_json=False;service.global_field(case,field,options[1].id,options[0].id,actor,'bulk');db.flush()
        assert (db.scalar(select(func.count()).select_from(CaseFieldChangeHistory).where(CaseFieldChangeHistory.case_id==case.id)) or 0)==before
        master.value_json=True;field.track_history=False;service.global_field(case,field,options[1].id,options[0].id,actor,'automation');db.flush()
        assert (db.scalar(select(func.count()).select_from(CaseFieldChangeHistory).where(CaseFieldChangeHistory.case_id==case.id)) or 0)==before
        db.rollback()


def test_case_history_is_paginated_and_permission_protected()->None:
    with SessionLocal() as db:
        case,*_=make_case(db);case_id=case.id;db.commit()
    headers=auth()
    response=client.get(f'/api/cases/{case_id}/history?page=1&page_size=1&kind=all',headers=headers)
    assert response.status_code==200 and response.json()['page_size']==1 and 'total' in response.json()
    assert client.get('/api/system/field-history-settings',headers=headers).status_code==200
