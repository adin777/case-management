import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.database.session import SessionLocal
from app.main import app
from app.modules.models import Case
from app.modules.operations.models import BusinessCalendar, Notification, SlaEvent
from app.modules.sla.service import BusinessCalendarService, SlaEngine

client=TestClient(app)


def headers()->dict[str,str]:
    token=client.post("/api/auth/login",json={"email":"admin@example.com","password":"Admin123!"}).json()["access_token"]
    return {"Authorization":f"Bearer {token}"}


def context(auth:dict[str,str])->tuple[dict,dict,dict]:
    environment=next(row for row in client.get("/api/environments",headers=auth).json() if row["code"]=="IT")
    request_type=client.get(f"/api/request-types?environment_id={environment['id']}",headers=auth).json()[0]
    priority=client.get(f"/api/environments/{environment['id']}/priorities",headers=auth).json()[0]
    return environment,request_type,priority


def create_case(auth:dict[str,str],environment:dict,request_type:dict,priority:dict,title:str)->dict:
    form=client.get(f"/api/forms/{request_type['form_version_id']}",headers=auth).json();values=[{"field_definition_id":field["id"],"value":"sla"} for field in form["fields"]]
    response=client.post("/api/cases",headers=auth,json={"environment_id":environment["id"],"request_type_id":request_type["id"],"title":title,"description":"SLA lifecycle","priority_id":priority["id"],"values":values})
    assert response.status_code==201,response.text
    return response.json()


def test_business_calendar_skips_outside_hours_and_holiday()->None:
    calendar=BusinessCalendar(name="בדיקה",environment_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),timezone="UTC",schedule_json={"0":[["08:00","17:00"]],"4":[["08:00","17:00"]]},holidays_json=["2026-09-07"],exceptions_json={},is_active=True)
    service=BusinessCalendarService(calendar)
    due=service.add_minutes(datetime(2026,9,4,16,50,tzinfo=UTC),20)
    assert due==datetime(2026,9,11,8,10,tzinfo=UTC)


def test_complete_sla_start_pause_resume_warning_breach_report_and_export()->None:
    auth=headers();environment,request_type,priority=context(auth)
    calendar=client.post(f"/api/environments/{environment['id']}/business-calendars",headers=auth,json={"name":"24/7","timezone":"UTC","schedule_json":{str(day):[["00:00","23:59"]] for day in range(7)},"holidays_json":[],"exceptions_json":{},"is_active":True})
    assert calendar.status_code==201
    policy=client.post(f"/api/environments/{environment['id']}/sla-policies",headers=auth,json={"name_he":"SLA בדיקה","request_type_id":request_type["id"],"priority_id":None,"priority_option_id":None,"response_minutes":10,"resolution_minutes":20,"warning_threshold_percent":50,"business_calendar_id":calendar.json()["id"],"conditions_json":{},"pause_rules_json":{"status_categories":["waiting"],"approval_pending":True},"notification_json":{"environment_managers":True},"precedence":10,"recalculate_on_change":True,"is_active":True})
    assert policy.status_code==201,policy.text
    first=create_case(auth,environment,request_type,priority,"SLA response met")
    indicator=client.get(f"/api/cases/{first['id']}/sla",headers=auth)
    assert indicator.status_code==200 and indicator.json()["response_status"]=="running"
    assert client.post(f"/api/cases/{first['id']}/comments",headers=auth,json={"body":"תגובה","visibility":"public"}).status_code==201
    assert client.get(f"/api/cases/{first['id']}/sla",headers=auth).json()["response_status"]=="met"
    second=create_case(auth,environment,request_type,priority,"SLA warning breach")
    with SessionLocal() as db:
        item=db.get(Case,uuid.UUID(second["id"]));assert item;engine=SlaEngine(db);instance=engine.active_instance(item.id)
        assert instance
        engine.pause(item,"waiting",now=instance.started_at+timedelta(minutes=1));engine.resume(item,now=instance.started_at+timedelta(minutes=3));engine.pause(item,"external",now=instance.started_at+timedelta(minutes=4));engine.resume(item,now=instance.started_at+timedelta(minutes=5));db.commit()
        assert instance.accumulated_pause_seconds==180
        assert instance.response_warning_at and instance.resolution_due_at
        warning_now=instance.response_warning_at+timedelta(seconds=1);assert engine.tick(warning_now)["warning"]>=1;db.commit();assert engine.tick(warning_now)["warning"]==0
        breach_now=instance.resolution_due_at+timedelta(seconds=1);assert engine.tick(breach_now)["breached"]>=1;db.commit();assert engine.tick(breach_now)["breached"]==0;db.commit()
        warning_events=db.scalar(select(func.count()).select_from(SlaEvent).where(SlaEvent.instance_id==instance.id,SlaEvent.event_type=="warning")) or 0;assert warning_events<=2
        notification_count=db.scalar(select(func.count()).select_from(Notification).where(Notification.entity_id==str(item.id),Notification.notification_type.in_(["sla_warning","sla_breached"]))) or 0;assert notification_count>=1
    report=client.get(f"/api/reports/sla?environment_id={environment['id']}",headers=auth);assert report.status_code==200 and report.json()["total"]>=2
    metrics=client.get(f"/api/reports/sla/metrics?environment_id={environment['id']}",headers=auth);assert metrics.status_code==200 and "response_compliance_percent" in metrics.json()
    exported=client.get(f"/api/reports/sla/export?environment_id={environment['id']}",headers=auth);assert exported.status_code==200 and exported.content[:2]==b"PK"


def test_sla_policy_conflict_is_blocked()->None:
    auth=headers();environment,request_type,_=context(auth);payload={"name_he":"Conflict","request_type_id":request_type["id"],"response_minutes":30,"resolution_minutes":60,"warning_threshold_percent":80,"conditions_json":{},"pause_rules_json":{},"notification_json":{},"precedence":999,"is_active":True}
    assert client.post(f"/api/environments/{environment['id']}/sla-policies",headers=auth,json=payload).status_code==201
    assert client.post(f"/api/environments/{environment['id']}/sla-policies",headers=auth,json={**payload,"name_he":"Conflict 2"}).status_code==409
