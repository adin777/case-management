from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.case_semantics.service import CaseSemanticFieldService
from app.modules.models import (
    AutomationExecutionLog,
    AutomationRule,
    Case,
    CaseFieldDefinition,
    CaseFieldValue,
    GlobalCaseFieldDefinition,
    GlobalCaseFieldValue,
)


def is_field_empty(value: Any, field_type: str | None = None) -> bool:
    """Business emptiness preserves valid numeric zero and boolean false values."""
    if value is None or value == "":
        return True
    return field_type == "multi_select" and isinstance(value, list) and len(value) == 0


class AutomationEngine:
    MAX_ACTIONS = 20

    @classmethod
    def run(cls, db: Session, item: Case, trigger_type: str, context: dict[str, Any]) -> None:
        rules = db.scalars(select(AutomationRule).where(
            AutomationRule.environment_id == item.environment_id,
            AutomationRule.trigger_type == trigger_type,
            AutomationRule.is_active.is_(True),
        ).order_by(AutomationRule.priority)).all()
        action_count = 0
        for rule in rules:
            executed: list[dict[str, Any]] = []
            error = None
            matched = cls._matches(db, item, rule.conditions_json or {}, context)
            try:
                if matched:
                    for action in rule.actions_json or []:
                        if action_count >= cls.MAX_ACTIONS:
                            raise RuntimeError("Automation chain action limit exceeded")
                        cls._apply(db,item,action)
                        executed.append(action)
                        action_count += 1
            except (RuntimeError, TypeError, ValueError) as exc:
                error = str(exc)
            db.add(AutomationExecutionLog(rule_id=rule.id, case_id=item.id,
                                          trigger_type=trigger_type, matched=matched,
                                          actions_executed=executed, error=error))

    @classmethod
    def _matches(cls, db: Session, item: Case, conditions: dict[str, Any],
                 context: dict[str, Any]) -> bool:
        rows = conditions.get("conditions", [])
        if not rows:
            return True
        results = []
        for row in rows:
            field_ref = row.get("field_id") or row.get("field")
            actual, field_type = cls._field_value(db, item, field_ref, context)
            expected, operator = row.get("value"), row.get("operator")
            if operator == "equals": matched = actual == expected
            elif operator == "not_equals": matched = actual != expected
            elif operator == "contains": matched = expected in actual if isinstance(actual, (str, list)) else False
            elif operator == "not_contains": matched = expected not in actual if isinstance(actual, (str, list)) else True
            elif operator == "in": matched = actual in expected if isinstance(expected, list) else False
            elif operator == "not_in": matched = actual not in expected if isinstance(expected, list) else True
            elif operator == "is_empty": matched = is_field_empty(actual, field_type)
            elif operator == "is_not_empty": matched = not is_field_empty(actual, field_type)
            elif operator == "greater_than": matched = actual is not None and expected is not None and actual > expected
            elif operator == "less_than": matched = actual is not None and expected is not None and actual < expected
            else: matched = False
            results.append(matched)
        return all(results) if conditions.get("logic", "AND") == "AND" else any(results)

    @staticmethod
    def _field_value(db: Session, item: Case, field_ref: Any,
                     context: dict[str, Any]) -> tuple[Any, str | None]:
        try:
            field_id = UUID(str(field_ref))
        except (ValueError, TypeError):
            return context.get(field_ref), None
        global_field = db.get(GlobalCaseFieldDefinition, field_id)
        if global_field:
            if global_field.semantic_binding:
                return CaseSemanticFieldService(db).value_id(item, global_field.semantic_binding), global_field.field_type
            global_value = db.get(GlobalCaseFieldValue, (item.id, field_id))
            return (global_value.value_json if global_value else None), global_field.field_type
        environment_field = db.get(CaseFieldDefinition, field_id)
        environment_value = db.scalar(select(CaseFieldValue).where(
            CaseFieldValue.case_id == item.id,
            CaseFieldValue.field_definition_id == field_id)) if environment_field else None
        if not environment_value:
            return None, environment_field.field_type if environment_field else None
        assert environment_field is not None
        for name in ("value_text", "value_number", "value_boolean", "value_date", "value_datetime",
                     "value_json", "value_user_id"):
            candidate = getattr(environment_value, name)
            if candidate is not None:
                return candidate, environment_field.field_type
        return None, environment_field.field_type

    @staticmethod
    def _apply(db:Session,item:Case,action:dict[str,Any])->None:
        action_type, value = action.get("type"), action.get("value")
        if action_type == "set_field":
            field_code = action.get("field_id") or action.get("field_code")
            value = action.get("value_id", action.get("value"))
            try:
                target_id = UUID(str(field_code))
            except (ValueError, TypeError):
                target_id = None
            target = db.get(GlobalCaseFieldDefinition, target_id) if target_id else None
            if target and target.semantic_binding:
                CaseSemanticFieldService(db).write(item, target.semantic_binding, UUID(str(value)),source="automation")
                return
            binding={"status":"case.status","priority":"case.priority",
                     "sub_priority":"case.sub_priority","assignee":"case.assignee"}.get(
                         field_code if isinstance(field_code, str) else ""
                     )
            if binding:
                CaseSemanticFieldService(db).write(item, binding, UUID(str(value)),source="automation")
            elif field_code == "assignee_group": item.assigned_group_id = UUID(value)
            else: raise ValueError(f"Unsupported automation target field: {field_code}")
            return
        if action_type == "assign_user": CaseSemanticFieldService(db).write(item,"case.assignee",UUID(value),source="automation")
        elif action_type == "assign_group": item.assigned_group_id = UUID(value)
        elif action_type == "set_status": CaseSemanticFieldService(db).write(item,"case.status",UUID(value),source="automation")
        elif action_type == "set_priority": CaseSemanticFieldService(db).write(item,"case.priority",UUID(value),source="automation")
        elif action_type == "set_sub_priority": CaseSemanticFieldService(db).write(item,"case.sub_priority",UUID(value),source="automation")
        else: raise ValueError(f"Unsupported automation action: {action_type}")
