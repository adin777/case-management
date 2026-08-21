import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import Session

from app.modules.models import (
    Case,
    CaseSemanticSyncConflict,
    GlobalCaseFieldDefinition,
    GlobalCaseFieldValue,
    GlobalPriorityDefinition,
    GlobalStatusDefinition,
    GlobalSubPriorityDefinition,
    User,
)

BINDINGS = {"case.status", "case.priority", "case.sub_priority", "case.assignee"}
COLUMN_NAMES = {
    "case.status": "workflow_status_id",
    "case.priority": "priority_id",
    "case.sub_priority": "sub_priority_id",
    "case.assignee": "assignee_id",
}
CATALOGS: dict[str, type[Any]] = {
    "case.status": GlobalStatusDefinition,
    "case.priority": GlobalPriorityDefinition,
    "case.sub_priority": GlobalSubPriorityDefinition,
    "case.assignee": User,
}


class CaseSemanticFieldService:
    """The only read/write boundary for semantic Global Case Fields.

    Case columns are query indexes. When a binding exists, GlobalCaseFieldValue is the
    business value and every write mirrors it to the corresponding indexed column.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def definition(self, binding: str) -> GlobalCaseFieldDefinition | None:
        return self.db.scalar(select(GlobalCaseFieldDefinition).where(
            GlobalCaseFieldDefinition.semantic_binding == binding,
            GlobalCaseFieldDefinition.is_active.is_(True),
        ))

    def indexed_column(self, binding: str) -> ColumnElement[Any]:
        if binding not in COLUMN_NAMES:
            raise ValueError(f"Unsupported semantic binding: {binding}")
        return getattr(Case, COLUMN_NAMES[binding])

    def value_id(self, item: Case, binding: str) -> uuid.UUID | None:
        field = self.definition(binding)
        if field:
            row = self.db.get(GlobalCaseFieldValue, (item.id, field.id))
            if row and row.value_json not in (None, ""):
                try:
                    return uuid.UUID(str(row.value_json))
                except ValueError:
                    return None
        return getattr(item, COLUMN_NAMES[binding])

    def validate_value(self, binding: str, value_id: uuid.UUID | None,
                       *, require_active: bool = True) -> Any | None:
        if value_id is None:
            return None
        model = CATALOGS[binding]
        value = self.db.get(model, value_id)
        if not value or (require_active and getattr(value, "is_active", True) is not True):
            raise HTTPException(422, {"code":"INVALID_SEMANTIC_VALUE","binding":binding,
                                      "value_id":str(value_id)})
        return value

    def options(self, binding: str) -> list[dict[str, Any]]:
        model=CATALOGS[binding]
        if binding == "case.assignee":
            return []
        rows=self.db.scalars(select(model).where(model.is_active.is_(True)).order_by(
            model.sort_order,model.label_he))
        return [{"id":str(row.id),"label_he":row.label_he,"label_en":row.label_en or "",
                 "is_active":True,"sort_order":row.sort_order} for row in rows]

    def write(self, item: Case, binding: str, value: uuid.UUID | str | None,
              *, require_active: bool = True) -> None:
        if binding not in BINDINGS:
            raise ValueError(f"Unsupported semantic binding: {binding}")
        parsed = uuid.UUID(str(value)) if value not in (None, "") else None
        self.validate_value(binding, parsed, require_active=require_active)
        field = self.definition(binding)
        if field:
            row = self.db.get(GlobalCaseFieldValue, (item.id, field.id))
            if row:
                row.value_json = str(parsed) if parsed else None
            else:
                self.db.add(GlobalCaseFieldValue(case_id=item.id, global_field_id=field.id,
                    value_json=str(parsed) if parsed else None))
        setattr(item, COLUMN_NAMES[binding], parsed)

    def label(self, item: Case, binding: str, *, language: str = "he") -> str:
        value_id = self.value_id(item, binding)
        if not value_id:
            return ""
        value = self.db.get(CATALOGS[binding], value_id)
        if not value:
            return ""
        if binding == "case.assignee":
            return str(value.display_name)
        return str(getattr(value, "label_en", None) if language == "en" else getattr(value, "label_he", "")
                   or getattr(value, "label_he", ""))

    def sync_case(self, item: Case) -> list[CaseSemanticSyncConflict]:
        conflicts: list[CaseSemanticSyncConflict] = []
        for binding in BINDINGS:
            field = self.definition(binding)
            if not field:
                continue
            row = self.db.get(GlobalCaseFieldValue, (item.id, field.id))
            raw_global = row.value_json if row else None
            optimized = getattr(item, COLUMN_NAMES[binding])
            parsed_global: uuid.UUID | None = None
            if raw_global not in (None, ""):
                try:
                    parsed_global = uuid.UUID(str(raw_global))
                except ValueError:
                    pass
            valid_global = bool(parsed_global and self.db.get(CATALOGS[binding], parsed_global))
            if raw_global not in (None, "") and not valid_global:
                conflicts.append(self._conflict(item,binding,raw_global,optimized,"invalid_global_value"))
            elif parsed_global and optimized and parsed_global != optimized:
                conflicts.append(self._conflict(item,binding,raw_global,optimized,"value_mismatch"))
            elif parsed_global and not optimized:
                setattr(item,COLUMN_NAMES[binding],parsed_global)
            elif optimized and (not row or row.value_json in (None, "")):
                if row:
                    row.value_json = str(optimized)
                else:
                    self.db.add(GlobalCaseFieldValue(case_id=item.id,global_field_id=field.id,
                        value_json=str(optimized)))
        return conflicts

    def _conflict(self,item:Case,binding:str,global_value:Any,optimized:uuid.UUID|None,
                  reason:str)->CaseSemanticSyncConflict:
        existing = self.db.scalar(select(CaseSemanticSyncConflict).where(
            CaseSemanticSyncConflict.case_id == item.id,
            CaseSemanticSyncConflict.semantic_binding == binding,
            CaseSemanticSyncConflict.reason == reason,
            CaseSemanticSyncConflict.resolved_at.is_(None)))
        if existing:
            return existing
        row=CaseSemanticSyncConflict(case_id=item.id,semantic_binding=binding,
            global_value_json=global_value,optimized_value_id=optimized,reason=reason)
        self.db.add(row)
        return row
