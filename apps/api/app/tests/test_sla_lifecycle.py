import uuid
from datetime import UTC, datetime, timedelta
from time import perf_counter
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.database.session import SessionLocal
from app.main import app
from app.modules.access.mapping import DOMAIN_DEFINITIONS
from app.modules.api import ALL_PERMISSIONS
from app.modules.models import Case
from app.modules.operations.models import BusinessCalendar, Notification, SlaEvent
from app.modules.sla.service import BusinessCalendarService, SlaEngine

client = TestClient(app)


def headers() -> dict[str, str]:
    token = client.post(
        "/api/auth/login", json={"email": "admin@example.com", "password": "Admin123!"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def context(auth: dict[str, str]) -> tuple[dict, dict, dict]:
    environment = next(
        row for row in client.get("/api/environments", headers=auth).json() if row["code"] == "IT"
    )
    request_type = client.get(f"/api/request-types?environment_id={environment['id']}", headers=auth).json()[
        0
    ]
    priority = client.get(f"/api/environments/{environment['id']}/priorities", headers=auth).json()[0]
    return environment, request_type, priority


def create_case(
    auth: dict[str, str], environment: dict, request_type: dict, priority: dict, title: str
) -> dict:
    form = client.get(f"/api/forms/{request_type['form_version_id']}", headers=auth).json()
    values = [{"field_definition_id": field["id"], "value": "sla"} for field in form["fields"]]
    response = client.post(
        "/api/cases",
        headers=auth,
        json={
            "environment_id": environment["id"],
            "request_type_id": request_type["id"],
            "title": title,
            "description": "SLA lifecycle",
            "priority_id": priority["id"],
            "values": values,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_business_calendar_skips_outside_hours_and_holiday() -> None:
    calendar = BusinessCalendar(
        name="בדיקה",
        environment_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        timezone="UTC",
        schedule_json={"0": [["08:00", "17:00"]], "4": [["08:00", "17:00"]]},
        holidays_json=["2026-09-07"],
        exceptions_json={},
        is_active=True,
    )
    service = BusinessCalendarService(calendar)
    due = service.add_minutes(datetime(2026, 9, 4, 16, 50, tzinfo=UTC), 20)
    assert due == datetime(2026, 9, 11, 8, 10, tzinfo=UTC)


def weekday_calendar(*, holidays: list[str] | None = None, timezone: str = "UTC") -> BusinessCalendar:
    return BusinessCalendar(
        name="calendar",
        environment_id=uuid.uuid4(),
        timezone=timezone,
        schedule_json={str(day): [["08:00", "17:00"]] for day in range(5)},
        holidays_json=holidays or [],
        exceptions_json={},
        is_active=True,
    )


def test_pause_extension_crosses_weekend_and_holiday_in_business_time() -> None:
    regular = BusinessCalendarService(weekday_calendar())
    pause_start = datetime(2026, 9, 4, 16, 0, tzinfo=UTC)
    resume_at = datetime(2026, 9, 7, 9, 0, tzinfo=UTC)
    assert regular.working_seconds_between(pause_start, resume_at) == 7200
    assert regular.add_seconds(datetime(2026, 9, 7, 10, 0, tzinfo=UTC), 7200) == datetime(
        2026, 9, 7, 12, 0, tzinfo=UTC
    )
    holiday = BusinessCalendarService(weekday_calendar(holidays=["2026-09-07"]))
    holiday_resume = datetime(2026, 9, 8, 9, 0, tzinfo=UTC)
    assert holiday.working_seconds_between(pause_start, holiday_resume) == 7200
    assert holiday.add_seconds(datetime(2026, 9, 8, 10, 0, tzinfo=UTC), 7200) == datetime(
        2026, 9, 8, 12, 0, tzinfo=UTC
    )


def test_dst_boundary_and_large_duration_are_interval_based() -> None:
    zone = ZoneInfo("America/New_York")
    calendar = weekday_calendar(timezone="America/New_York")
    calendar.schedule_json = {"6": [["01:00", "04:00"]]}
    service = BusinessCalendarService(calendar)
    start = datetime(2026, 3, 8, 1, 0, tzinfo=zone)
    assert (
        service.add_minutes(start, 120).astimezone(zone).strftime("%Y-%m-%d %H:%M %z")
        == "2026-03-08 04:00 -0400"
    )
    began = perf_counter()
    due = BusinessCalendarService(weekday_calendar()).add_minutes(
        datetime(2026, 1, 5, 8, 0, tzinfo=UTC), 525_600
    )
    assert due.year > 2026 and perf_counter() - began < 1.0


def test_sla_permission_domains_have_one_consistent_namespace() -> None:
    expected = {"sla.view", "sla.configure", "sla.report"}
    assert expected <= set(ALL_PERMISSIONS)
    assert not ({"sla.read", "sla.manage", "report.sla"} & set(ALL_PERMISSIONS))
    mapped = {code for row in DOMAIN_DEFINITIONS for cell in row[5:] for code in cell.split(",")}
    assert expected <= mapped and not ({"sla.read", "sla.manage", "report.sla"} & mapped)


def test_business_calendar_rejects_missing_timezone_and_empty_schedule() -> None:
    auth = headers()
    environment, _, _ = context(auth)
    payload = {
        "name": "Invalid calendar",
        "timezone": "Invalid/Timezone",
        "schedule_json": {"0": [["08:00", "17:00"]]},
        "holidays_json": [],
        "exceptions_json": {},
        "is_active": True,
    }
    invalid_zone = client.post(
        f"/api/environments/{environment['id']}/business-calendars", headers=auth, json=payload
    )
    assert invalid_zone.status_code == 422
    assert "Timezone configuration is unavailable" in invalid_zone.text
    empty = client.post(
        f"/api/environments/{environment['id']}/business-calendars",
        headers=auth,
        json={**payload, "timezone": "UTC", "schedule_json": {}},
    )
    assert empty.status_code == 422


def test_complete_sla_start_pause_resume_warning_breach_report_and_export() -> None:
    auth = headers()
    environment, request_type, priority = context(auth)
    calendar = client.post(
        f"/api/environments/{environment['id']}/business-calendars",
        headers=auth,
        json={
            "name": "24/7",
            "timezone": "UTC",
            "schedule_json": {str(day): [["00:00", "23:59"]] for day in range(7)},
            "holidays_json": [],
            "exceptions_json": {},
            "is_active": True,
        },
    )
    assert calendar.status_code == 201
    policy = client.post(
        f"/api/environments/{environment['id']}/sla-policies",
        headers=auth,
        json={
            "name_he": "SLA בדיקה",
            "request_type_id": request_type["id"],
            "priority_id": None,
            "priority_option_id": None,
            "response_minutes": 10,
            "resolution_minutes": 20,
            "warning_threshold_percent": 50,
            "business_calendar_id": calendar.json()["id"],
            "conditions_json": {},
            "pause_rules_json": {"status_categories": ["waiting"], "approval_pending": True},
            "notification_json": {"environment_managers": True},
            "precedence": 10,
            "recalculate_on_change": True,
            "is_active": True,
        },
    )
    assert policy.status_code == 201, policy.text
    first = create_case(auth, environment, request_type, priority, "SLA response met")
    indicator = client.get(f"/api/cases/{first['id']}/sla", headers=auth)
    assert indicator.status_code == 200 and indicator.json()["response_status"] == "running"
    assert (
        client.post(
            f"/api/cases/{first['id']}/comments", headers=auth, json={"body": "תגובה", "visibility": "public"}
        ).status_code
        == 201
    )
    assert client.get(f"/api/cases/{first['id']}/sla", headers=auth).json()["response_status"] == "met"
    second = create_case(auth, environment, request_type, priority, "SLA warning breach")
    with SessionLocal() as db:
        item = db.get(Case, uuid.UUID(second["id"]))
        assert item
        engine = SlaEngine(db)
        instance = engine.active_instance(item.id)
        assert instance
        engine.pause(item, "waiting", now=instance.started_at + timedelta(minutes=1))
        engine.resume(item, now=instance.started_at + timedelta(minutes=3))
        engine.pause(item, "external", now=instance.started_at + timedelta(minutes=4))
        engine.resume(item, now=instance.started_at + timedelta(minutes=5))
        db.commit()
        assert instance.accumulated_pause_seconds == 180
        assert instance.response_warning_at and instance.resolution_due_at
        warning_now = instance.response_warning_at + timedelta(seconds=1)
        assert engine.tick(warning_now)["warning"] >= 1
        db.commit()
        assert engine.tick(warning_now)["warning"] == 0
        breach_now = instance.resolution_due_at + timedelta(seconds=1)
        assert engine.tick(breach_now)["breached"] >= 1
        db.commit()
        assert engine.tick(breach_now)["breached"] == 0
        db.commit()
        warning_events = (
            db.scalar(
                select(func.count())
                .select_from(SlaEvent)
                .where(SlaEvent.instance_id == instance.id, SlaEvent.event_type == "warning")
            )
            or 0
        )
        assert warning_events <= 2
        notification_count = (
            db.scalar(
                select(func.count())
                .select_from(Notification)
                .where(
                    Notification.entity_id == str(item.id),
                    Notification.notification_type.in_(["sla_warning", "sla_breached"]),
                )
            )
            or 0
        )
        assert notification_count >= 1
    report = client.get(f"/api/reports/sla?environment_id={environment['id']}", headers=auth)
    assert report.status_code == 200 and report.json()["total"] >= 2
    filtered = client.get(
        f"/api/reports/sla?request_type_id={request_type['id']}&priority_option_id={priority['id']}&environment_id={environment['id']}",
        headers=auth,
    )
    assert filtered.status_code == 200 and filtered.json()["total"] >= 2
    assert client.get(f"/api/reports/sla?request_type_id={uuid.uuid4()}", headers=auth).json()["total"] == 0
    assert client.get("/api/reports/sla?created_from=2099-01-01T00:00:00Z", headers=auth).json()["total"] == 0
    options = client.get("/api/reports/sla/options", headers=auth)
    assert options.status_code == 200 and {
        "environments",
        "request_types",
        "priorities",
        "assignees",
        "policies",
    } <= set(options.json())
    metrics = client.get(
        f"/api/reports/sla/metrics?environment_id={environment['id']}&request_type_id={request_type['id']}",
        headers=auth,
    )
    assert metrics.status_code == 200 and {
        "compliance_percent",
        "response_compliance_percent",
        "resolution_compliance_percent",
        "average_first_response_seconds",
        "average_resolution_seconds",
        "average_paused_seconds",
    } <= set(metrics.json())
    exported = client.get(f"/api/reports/sla/export?environment_id={environment['id']}", headers=auth)
    assert exported.status_code == 200 and exported.content[:2] == b"PK"


def test_sla_policy_conflict_is_blocked() -> None:
    auth = headers()
    environment, request_type, _ = context(auth)
    payload = {
        "name_he": "Conflict",
        "request_type_id": request_type["id"],
        "response_minutes": 30,
        "resolution_minutes": 60,
        "warning_threshold_percent": 80,
        "conditions_json": {},
        "pause_rules_json": {},
        "notification_json": {},
        "precedence": 999,
        "is_active": True,
    }
    assert (
        client.post(
            f"/api/environments/{environment['id']}/sla-policies", headers=auth, json=payload
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/environments/{environment['id']}/sla-policies",
            headers=auth,
            json={**payload, "name_he": "Conflict 2"},
        ).status_code
        == 409
    )
