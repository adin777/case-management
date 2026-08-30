import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import Session

from app.modules.models import (
    Case,
    CaseSemanticSyncConflict,
    GlobalCaseFieldDefinition,
    GlobalCaseFieldOption,
    GlobalCaseFieldValue,
    User,
)

BINDINGS = {"case.status", "case.priority", "case.sub_priority", "case.assignee"}
COLUMN_NAMES = {"case.status":"workflow_status_id", "case.priority":"priority_id",
                "case.sub_priority":"sub_priority_id", "case.assignee":"assignee_id"}


class CaseSemanticFieldService:
    """Canonical access to semantic Global Field values and options."""
    def __init__(self, db: Session) -> None: self.db = db

    def definition(self, binding: str) -> GlobalCaseFieldDefinition | None:
        return self.db.scalar(select(GlobalCaseFieldDefinition).where(
            GlobalCaseFieldDefinition.semantic_binding == binding,
            GlobalCaseFieldDefinition.is_active.is_(True)))

    def indexed_column(self, binding: str) -> ColumnElement[Any]:
        if binding not in COLUMN_NAMES: raise ValueError(f"Unsupported semantic binding: {binding}")
        return getattr(Case, COLUMN_NAMES[binding])

    @staticmethod
    def scalar_value(value: Any) -> Any:
        return value[0] if isinstance(value, list) and len(value) == 1 else value

    def value_id(self, item: Case, binding: str) -> uuid.UUID | None:
        field = self.definition(binding)
        if not field: return getattr(item, COLUMN_NAMES[binding])
        row = self.db.get(GlobalCaseFieldValue, (item.id, field.id))
        raw = self.scalar_value(row.value_json) if row else None
        try: return uuid.UUID(str(raw)) if raw not in (None, "") and not isinstance(raw, list) else None
        except ValueError: return None

    def option(self, binding: str, value_id: uuid.UUID | None) -> GlobalCaseFieldOption | None:
        field = self.definition(binding)
        if not field or not value_id:
            return None
        row = self.db.get(GlobalCaseFieldOption, value_id)
        return row if row and row.global_field_id == field.id else None

    def option_for_config_id(self, binding: str, value_id: uuid.UUID) -> GlobalCaseFieldOption | None:
        direct = self.option(binding, value_id)
        if direct:
            return direct
        return next((row for row in self.db.scalars(select(GlobalCaseFieldOption))
                     if (row.metadata_json or {}).get("legacy_id") == str(value_id)), None)

    def validate_value(self, binding: str, value_id: uuid.UUID | None,
                       *, require_active: bool = True) -> Any | None:
        if value_id is None: return None
        value = self.db.get(User, value_id) if binding == "case.assignee" else self.option(binding, value_id)
        if not value or (require_active and not getattr(value, "is_active", True)):
            raise HTTPException(422, {"code":"INVALID_SEMANTIC_VALUE", "binding":binding,
                                      "value_id":str(value_id)})
        return value

    def option_rows(self, binding: str, *, active_only: bool = True) -> list[GlobalCaseFieldOption]:
        field = self.definition(binding)
        if not field or binding == "case.assignee": return []
        query = select(GlobalCaseFieldOption).where(GlobalCaseFieldOption.global_field_id == field.id)
        if active_only:
            query = query.where(GlobalCaseFieldOption.is_active.is_(True))
        return list(self.db.scalars(query.order_by(
            GlobalCaseFieldOption.sort_order, GlobalCaseFieldOption.label_he)))

    def options(self, binding: str) -> list[dict[str, Any]]:
        rows = self.option_rows(binding)
        return [{"id":str(row.id), "label_he":row.label_he, "label_en":row.label_en,
                 "is_active":row.is_active, "sort_order":row.sort_order,
                 "metadata":row.metadata_json or {}} for row in rows]

    def options_for_field(self, field_id: uuid.UUID, *, active_only: bool = True) -> list[dict[str, Any]]:
        query = select(GlobalCaseFieldOption).where(GlobalCaseFieldOption.global_field_id == field_id)
        if active_only:
            query = query.where(GlobalCaseFieldOption.is_active.is_(True))
        rows = self.db.scalars(query.order_by(GlobalCaseFieldOption.sort_order,
                                              GlobalCaseFieldOption.label_he))
        return [{"id":str(row.id), "label_he":row.label_he, "label_en":row.label_en,
                 "is_active":row.is_active, "sort_order":row.sort_order,
                 "metadata":row.metadata_json or {}} for row in rows]

    def write(self, item: Case, binding: str, value: uuid.UUID | str | None,
              *, require_active: bool = True) -> None:
        parsed = uuid.UUID(str(value)) if value not in (None, "") else None
        self.validate_value(binding, parsed, require_active=require_active)
        field = self.definition(binding)
        if field:
            row = self.db.get(GlobalCaseFieldValue, (item.id, field.id))
            if parsed is None:
                if row:
                    self.db.delete(row)
            elif row:
                row.value_json = str(parsed)
            else:
                self.db.add(GlobalCaseFieldValue(case_id=item.id, global_field_id=field.id,
                    value_json=str(parsed)))
        setattr(item, COLUMN_NAMES[binding], parsed)

    def label(self, item: Case, binding: str, *, language: str = "he") -> str:
        value_id = self.value_id(item, binding)
        if binding == "case.assignee":
            user = self.db.get(User, value_id) if value_id else None
            return user.display_name if user else ("ערך לא מזוהה" if value_id else "")
        option = self.option(binding, value_id)
        if not option: return "ערך לא מזוהה" if value_id else ""
        return option.label_en if language == "en" and option.label_en else option.label_he

    def sync_case(self, item: Case) -> list[CaseSemanticSyncConflict]:
        conflicts: list[CaseSemanticSyncConflict] = []
        for binding in BINDINGS:
            field = self.definition(binding)
            if not field: continue
            row = self.db.get(GlobalCaseFieldValue, (item.id, field.id)); raw = row.value_json if row else None
            scalar = self.scalar_value(raw)
            if isinstance(raw, list) and len(raw) == 1 and row: row.value_json = scalar
            try: value_id = uuid.UUID(str(scalar)) if scalar not in (None, "") and not isinstance(scalar, list) else None
            except ValueError: value_id = None
            indexed = getattr(item, COLUMN_NAMES[binding])
            valid = (self.db.get(User, value_id) if binding == "case.assignee" else self.option(binding, value_id)) if value_id else None
            if scalar and not valid: conflicts.append(self._conflict(item,binding,raw,indexed,"invalid_global_option"))
            elif value_id: setattr(item, COLUMN_NAMES[binding], value_id)
            elif indexed: conflicts.append(self._conflict(item,binding,raw,indexed,"missing_global_value"))
        return conflicts

    def _conflict(self,item:Case,binding:str,global_value:Any,optimized:uuid.UUID|None,
                  reason:str)->CaseSemanticSyncConflict:
        existing = self.db.scalar(select(CaseSemanticSyncConflict).where(
            CaseSemanticSyncConflict.case_id == item.id, CaseSemanticSyncConflict.semantic_binding == binding,
            CaseSemanticSyncConflict.reason == reason, CaseSemanticSyncConflict.resolved_at.is_(None)))
        if existing: return existing
        row=CaseSemanticSyncConflict(case_id=item.id,semantic_binding=binding,
            global_value_json=global_value,optimized_value_id=optimized,reason=reason)
        self.db.add(row); return row
