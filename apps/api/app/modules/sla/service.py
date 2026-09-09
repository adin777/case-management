import uuid
from datetime import UTC, date, datetime, time, timedelta, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.case_semantics.service import CaseSemanticFieldService
from app.modules.models import Case, EnvironmentMembership, GlobalCaseFieldValue
from app.modules.operations.models import (
    BusinessCalendar,
    Notification,
    SlaEvent,
    SlaInstance,
    SlaPause,
    SlaPolicy,
)


def aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class BusinessCalendarService:
    def __init__(self, calendar: BusinessCalendar | None):
        self.calendar = calendar

    def timezone(self) -> tzinfo:
        key = self.calendar.timezone if self.calendar else "UTC"
        if key == "UTC":
            return UTC
        try:
            return ZoneInfo(key)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Timezone configuration is unavailable: {key}") from exc

    def intervals(self, day: date) -> list[tuple[datetime, datetime]]:
        if not self.calendar:
            return []
        key = day.isoformat()
        if key in set(self.calendar.holidays_json or []):
            return []
        configured = (self.calendar.exceptions_json or {}).get(
            key, (self.calendar.schedule_json or {}).get(str(day.weekday()), [])
        )
        zone = self.timezone()
        result = []
        for start, end in configured:
            start_time = time.fromisoformat(start)
            end_time = time.fromisoformat(end)
            local_start = datetime.combine(day, start_time, zone)
            local_end = datetime.combine(day, end_time, zone)
            if local_end > local_start:
                result.append((local_start.astimezone(UTC), local_end.astimezone(UTC)))
        return result

    def working(self, instant: datetime) -> bool:
        if not self.calendar:
            return True
        current = aware(instant)
        local_day = current.astimezone(self.timezone()).date()
        return any(start <= current < end for start, end in self.intervals(local_day))

    def working_seconds_between(self, start: datetime, end: datetime) -> int:
        start = aware(start)
        end = aware(end)
        if end <= start:
            return 0
        if not self.calendar:
            return int((end - start).total_seconds())
        zone = self.timezone()
        day = start.astimezone(zone).date()
        last = end.astimezone(zone).date()
        seconds = 0
        while day <= last:
            for interval_start, interval_end in self.intervals(day):
                overlap_start = max(start, interval_start)
                overlap_end = min(end, interval_end)
                if overlap_end > overlap_start:
                    seconds += int((overlap_end - overlap_start).total_seconds())
            day += timedelta(days=1)
        return seconds

    def add_seconds(self, start: datetime, seconds: int) -> datetime:
        cursor = aware(start).astimezone(UTC)
        if seconds <= 0:
            return cursor
        if not self.calendar:
            return cursor + timedelta(seconds=seconds)
        if not any(self.calendar.schedule_json or {}):
            raise ValueError("Business calendar has no working intervals")
        zone = self.timezone()
        day = cursor.astimezone(zone).date()
        remaining = seconds
        while True:
            for interval_start, interval_end in self.intervals(day):
                current = max(cursor, interval_start)
                if current >= interval_end:
                    continue
                available = int((interval_end - current).total_seconds())
                if remaining <= available:
                    return current + timedelta(seconds=remaining)
                remaining -= available
            day += timedelta(days=1)
            cursor = datetime.combine(day, time.min, zone).astimezone(UTC)

    def add_minutes(self, start: datetime, minutes: int) -> datetime:
        return self.add_seconds(aware(start).replace(second=0, microsecond=0), minutes * 60)


class SlaEngine:
    def __init__(self, db: Session):
        self.db = db

    def active_instance(self, case_id: uuid.UUID) -> SlaInstance | None:
        return self.db.scalar(
            select(SlaInstance)
            .where(SlaInstance.case_id == case_id, SlaInstance.superseded_at.is_(None))
            .order_by(SlaInstance.started_at.desc())
        )

    def policy_matches(self, policy: SlaPolicy, item: Case) -> bool:
        if policy.request_type_id and policy.request_type_id != item.request_type_id:
            return False
        if policy.priority_option_id and policy.priority_option_id != CaseSemanticFieldService(
            self.db
        ).value_id(item, "case.priority"):
            return False
        values = {
            str(row.global_field_id): row.value_json
            for row in self.db.scalars(
                select(GlobalCaseFieldValue).where(GlobalCaseFieldValue.case_id == item.id)
            )
        }
        return all(
            values.get(str(field_id)) == expected
            for field_id, expected in (policy.conditions_json or {}).items()
        )

    def matching_policy(self, item: Case) -> SlaPolicy | None:
        candidates = [
            row
            for row in self.db.scalars(
                select(SlaPolicy).where(
                    SlaPolicy.environment_id == item.environment_id, SlaPolicy.is_active.is_(True)
                )
            )
            if self.policy_matches(row, item)
        ]
        ranked = sorted(
            candidates,
            key=lambda row: (
                row.precedence,
                bool(row.request_type_id) + bool(row.priority_option_id) + len(row.conditions_json or {}),
            ),
            reverse=True,
        )
        return ranked[0] if ranked else None

    def start(
        self, item: Case, now: datetime | None = None, *, supersede: bool = False
    ) -> SlaInstance | None:
        now = aware(now or datetime.now(UTC))
        current = self.active_instance(item.id)
        if current and not supersede:
            return current
        if current:
            current.superseded_at = now
            self.event(current, item, "all", "superseded", now)
        policy = self.matching_policy(item)
        if not policy:
            return None
        calendar = (
            self.db.get(BusinessCalendar, policy.business_calendar_id)
            if policy.business_calendar_id
            else None
        )
        clock = BusinessCalendarService(calendar)
        threshold = policy.warning_threshold_percent / 100
        instance = SlaInstance(
            case_id=item.id,
            policy_id=policy.id,
            started_at=now,
            response_due_at=clock.add_minutes(now, policy.response_minutes),
            resolution_due_at=clock.add_minutes(now, policy.resolution_minutes),
            response_warning_at=clock.add_minutes(now, max(1, int(policy.response_minutes * threshold))),
            resolution_warning_at=clock.add_minutes(now, max(1, int(policy.resolution_minutes * threshold))),
            response_status="running",
            resolution_status="running",
            accumulated_pause_seconds=0,
            last_calculated_at=now,
        )
        self.db.add(instance)
        self.db.flush()
        item.sla_policy_id = policy.id
        item.response_due_at = instance.response_due_at
        item.resolution_due_at = instance.resolution_due_at
        item.sla_response_status = instance.response_status
        item.sla_resolution_status = instance.resolution_status
        self.event(instance, item, "all", "started", now, {"policy_id": str(policy.id)})
        return instance

    def event(
        self,
        instance: SlaInstance,
        item: Case,
        target: str,
        event_type: str,
        now: datetime,
        details: dict | None = None,
        *,
        once: bool = False,
    ) -> bool:
        if once and self.db.scalar(
            select(SlaEvent.id).where(
                SlaEvent.instance_id == instance.id,
                SlaEvent.target == target,
                SlaEvent.event_type == event_type,
            )
        ):
            return False
        self.db.add(
            SlaEvent(
                instance_id=instance.id,
                case_id=item.id,
                target=target,
                event_type=event_type,
                occurred_at=now,
                details_json=details or {},
            )
        )
        return True

    def first_response(self, item: Case, now: datetime | None = None) -> None:
        now = aware(now or datetime.now(UTC))
        instance = self.active_instance(item.id)
        if not instance or instance.first_response_at:
            return
        instance.first_response_at = now
        instance.response_status = (
            "met" if not instance.response_due_at or now <= aware(instance.response_due_at) else "breached"
        )
        item.first_response_at = now
        item.sla_response_status = instance.response_status
        self.event(instance, item, "response", instance.response_status, now, once=True)

    def pause(
        self, item: Case, reason: str, actor_id: uuid.UUID | None = None, now: datetime | None = None
    ) -> None:
        now = aware(now or datetime.now(UTC))
        instance = self.active_instance(item.id)
        if not instance or instance.active_pause_started_at:
            return
        instance.active_pause_started_at = now
        if instance.resolution_status in {"running", "warning"}:
            instance.resolution_status = "paused"
            item.sla_resolution_status = "paused"
        if instance.response_status in {"running", "warning"}:
            instance.response_status = "paused"
            item.sla_response_status = "paused"
        self.db.add(SlaPause(instance_id=instance.id, started_at=now, reason=reason, actor_id=actor_id))
        self.event(instance, item, "all", "paused", now, {"reason": reason})

    def resume(self, item: Case, actor_id: uuid.UUID | None = None, now: datetime | None = None) -> None:
        now = aware(now or datetime.now(UTC))
        instance = self.active_instance(item.id)
        if not instance or not instance.active_pause_started_at:
            return
        started = aware(instance.active_pause_started_at)
        wall_seconds = max(0, int((now - started).total_seconds()))
        policy = self.db.get(SlaPolicy, instance.policy_id)
        calendar = (
            self.db.get(BusinessCalendar, policy.business_calendar_id)
            if policy and policy.business_calendar_id
            else None
        )
        clock = BusinessCalendarService(calendar)
        seconds = clock.working_seconds_between(started, now)
        instance.accumulated_pause_seconds += seconds
        instance.active_pause_started_at = None
        pause = self.db.scalar(
            select(SlaPause)
            .where(SlaPause.instance_id == instance.id, SlaPause.ended_at.is_(None))
            .order_by(SlaPause.started_at.desc())
        )
        if pause:
            pause.ended_at = now
            pause.duration_seconds = wall_seconds
        for field in ("response_due_at", "resolution_due_at", "response_warning_at", "resolution_warning_at"):
            value = getattr(instance, field)
            setattr(instance, field, clock.add_seconds(aware(value), seconds) if value else None)
        if not instance.first_response_at:
            instance.response_status = "running"
            item.sla_response_status = "running"
        if not instance.resolved_at:
            instance.resolution_status = "running"
            item.sla_resolution_status = "running"
        item.response_due_at = instance.response_due_at
        item.resolution_due_at = instance.resolution_due_at
        self.event(
            instance,
            item,
            "all",
            "resumed",
            now,
            {"pause_seconds": seconds, "actor_id": str(actor_id) if actor_id else None},
        )

    def status_changed(
        self,
        item: Case,
        semantic_category: str,
        actor_id: uuid.UUID | None = None,
        now: datetime | None = None,
    ) -> None:
        instance = self.active_instance(item.id)
        if not instance:
            return
        policy = self.db.get(SlaPolicy, instance.policy_id)
        pause_categories = (
            set((policy.pause_rules_json or {}).get("status_categories", [])) if policy else set()
        )
        if semantic_category in pause_categories:
            self.pause(item, f"status:{semantic_category}", actor_id, now)
        else:
            self.resume(item, actor_id, now)
        if semantic_category in {"resolved", "closed"}:
            self.resolve(item, now)

    def resolve(self, item: Case, now: datetime | None = None) -> None:
        now = aware(now or datetime.now(UTC))
        instance = self.active_instance(item.id)
        if not instance or instance.resolved_at:
            return
        if instance.active_pause_started_at:
            self.resume(item, now=now)
        instance.resolved_at = now
        instance.resolution_status = (
            "met"
            if not instance.resolution_due_at or now <= aware(instance.resolution_due_at)
            else "breached"
        )
        item.resolved_at = now
        item.sla_resolution_status = instance.resolution_status
        self.event(instance, item, "resolution", instance.resolution_status, now, once=True)

    def relevant_field_changed(self, item: Case) -> None:
        instance = self.active_instance(item.id)
        policy = self.db.get(SlaPolicy, instance.policy_id) if instance else None
        if policy and policy.recalculate_on_change:
            self.start(item, supersede=True)

    def approval_changed(self, item: Case, pending: bool, actor_id: uuid.UUID | None = None) -> None:
        instance = self.active_instance(item.id)
        policy = self.db.get(SlaPolicy, instance.policy_id) if instance else None
        if not policy or not (policy.pause_rules_json or {}).get("approval_pending"):
            return
        if pending:
            self.pause(item, "approval_pending", actor_id)
        else:
            self.resume(item, actor_id)

    def recipients(self, item: Case, policy: SlaPolicy) -> set[uuid.UUID]:
        config = policy.notification_json or {}
        result = {uuid.UUID(value) for value in config.get("user_ids", [])}
        if config.get("assignee") and item.assignee_id:
            result.add(item.assignee_id)
        if config.get("environment_managers"):
            result.update(
                self.db.scalars(
                    select(EnvironmentMembership.user_id).where(
                        EnvironmentMembership.environment_id == item.environment_id,
                        EnvironmentMembership.is_environment_manager.is_(True),
                        EnvironmentMembership.is_active.is_(True),
                    )
                )
            )
        return result

    def notify(self, item: Case, policy: SlaPolicy, event_type: str) -> None:
        for user_id in self.recipients(item, policy):
            self.db.add(
                Notification(
                    user_id=user_id,
                    notification_type=f"sla_{event_type}",
                    title_he="עדכון SLA",
                    body_he=f"קריאה {item.case_number}: {event_type}",
                    entity_type="case",
                    entity_id=str(item.id),
                )
            )

    def tick(self, now: datetime | None = None) -> dict[str, int]:
        now = aware(now or datetime.now(UTC))
        counts = {"warning": 0, "breached": 0}
        instances = self.db.scalars(select(SlaInstance).where(SlaInstance.superseded_at.is_(None)))
        for instance in instances:
            item = self.db.get(Case, instance.case_id)
            policy = self.db.get(SlaPolicy, instance.policy_id)
            if not item or not policy or instance.active_pause_started_at:
                continue
            for target in ("response", "resolution"):
                status = getattr(instance, f"{target}_status")
                warning = getattr(instance, f"{target}_warning_at")
                due = getattr(instance, f"{target}_due_at")
                achieved = getattr(instance, "first_response_at" if target == "response" else "resolved_at")
                if achieved or status in {"met", "cancelled", "breached"}:
                    continue
                if due and now >= aware(due):
                    setattr(instance, f"{target}_status", "breached")
                    setattr(item, f"sla_{target}_status", "breached")
                    if self.event(instance, item, target, "breached", now, once=True):
                        counts["breached"] += 1
                        self.notify(item, policy, "breached")
                elif warning and now >= aware(warning):
                    setattr(instance, f"{target}_status", "warning")
                    setattr(item, f"sla_{target}_status", "warning")
                    if self.event(instance, item, target, "warning", now, once=True):
                        counts["warning"] += 1
                        self.notify(item, policy, "warning")
            instance.last_calculated_at = now
        return counts
