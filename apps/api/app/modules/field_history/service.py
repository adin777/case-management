import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.modules.models import (
    Case,
    CaseFieldChangeHistory,
    FieldDefinition,
    GlobalCaseFieldDefinition,
    GlobalCaseFieldOption,
    SystemFieldSetting,
    SystemSetting,
    User,
)


def normalized(value: Any) -> Any:
    if isinstance(value, uuid.UUID): return str(value)
    if isinstance(value, (datetime, date)): return value.isoformat()
    if isinstance(value, Decimal): return str(value)
    return value


class FieldHistoryService:
    def __init__(self, db: Session) -> None: self.db = db

    def enabled(self) -> bool:
        row = self.db.get(SystemSetting, "field_history_enabled")
        return True if row is None else bool(row.value_json)

    def display(self, value: Any, field_type: str | None = None) -> str | None:
        if value in (None, "", []): return None
        if field_type in {"user", "case.assignee"}:
            try: user = self.db.get(User, uuid.UUID(str(value)))
            except (ValueError, TypeError): user = None
            return user.display_name if user else str(value)
        if field_type in {"single_select", "case.status", "case.priority", "case.sub_priority"}:
            try: option = self.db.get(GlobalCaseFieldOption, uuid.UUID(str(value)))
            except (ValueError, TypeError): option = None
            return option.label_he if option else str(value)
        if isinstance(value, list): return ", ".join(filter(None, (self.display(row, "single_select") for row in value)))
        if isinstance(value, bool): return "כן" if value else "לא"
        return str(value)

    def record(self, item: Case, *, field_scope: str, field_key: str, label: str,
               old: Any, new: Any, actor: User | None, source: str,
               track_history: bool, definition_id: uuid.UUID | None = None,
               semantic_binding: str | None = None, field_type: str | None = None) -> None:
        old_value, new_value = normalized(old), normalized(new)
        if not self.enabled() or not track_history or old_value == new_value: return
        real_actor_id = getattr(actor, "_real_actor_user_id", None) if actor else None
        self.db.add(CaseFieldChangeHistory(
            case_id=item.id, environment_id=item.environment_id, field_scope=field_scope,
            field_definition_id=definition_id, semantic_binding=semantic_binding,
            field_key=field_key, field_label_snapshot=label,
            old_value_json=old_value, new_value_json=new_value,
            old_display_value=self.display(old_value, field_type),
            new_display_value=self.display(new_value, field_type), changed_by=actor.id if actor else None,
            changed_by_name_snapshot=actor.display_name if actor else "מערכת",
            source=source, real_actor_id=real_actor_id,
            effective_user_id=actor.id if real_actor_id and actor else None,
        ))

    def semantic(self, item: Case, definition: GlobalCaseFieldDefinition, old: Any, new: Any,
                 actor: User | None, source: str) -> None:
        self.record(item, field_scope="global", field_key=definition.key,
            label=definition.label_he, old=old, new=new, actor=actor, source=source,
            track_history=definition.track_history, definition_id=definition.id,
            semantic_binding=definition.semantic_binding, field_type=definition.semantic_binding)

    def global_field(self, item: Case, definition: GlobalCaseFieldDefinition, old: Any, new: Any,
                     actor: User | None, source: str) -> None:
        self.record(item, field_scope="global", field_key=definition.key, label=definition.label_he,
            old=old, new=new, actor=actor, source=source, track_history=definition.track_history,
            definition_id=definition.id, semantic_binding=definition.semantic_binding,
            field_type=definition.field_type)

    def environment_field(self, item: Case, definition: FieldDefinition, old: Any, new: Any,
                          actor: User | None, source: str) -> None:
        self.record(item, field_scope="environment", field_key=definition.key,
            label=definition.label_he, old=old, new=new, actor=actor, source=source,
            track_history=definition.track_history, definition_id=definition.id,
            field_type=definition.field_type)

    def core(self, item: Case, key: str, label: str, old: Any, new: Any,
             actor: User | None, source: str, field_type: str | None = None) -> None:
        setting = self.db.get(SystemFieldSetting, key)
        self.record(item, field_scope="core", field_key=key, label=label, old=old, new=new,
            actor=actor, source=source, track_history=bool(setting and setting.track_history),
            field_type=field_type)
