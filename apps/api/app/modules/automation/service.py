from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.models import AutomationExecutionLog, AutomationRule, Case


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
            matched = cls._matches(rule.conditions_json or {}, context)
            try:
                if matched:
                    for action in rule.actions_json or []:
                        if action_count >= cls.MAX_ACTIONS:
                            raise RuntimeError("Automation chain action limit exceeded")
                        cls._apply(item, action)
                        executed.append(action)
                        action_count += 1
            except (RuntimeError, TypeError, ValueError) as exc:
                error = str(exc)
            db.add(AutomationExecutionLog(rule_id=rule.id, case_id=item.id,
                                          trigger_type=trigger_type, matched=matched,
                                          actions_executed=executed, error=error))

    @staticmethod
    def _matches(conditions: dict[str, Any], context: dict[str, Any]) -> bool:
        rows = conditions.get("conditions", [])
        if not rows:
            return True
        results = []
        for row in rows:
            actual, expected, operator = context.get(row.get("field")), row.get("value"), row.get("operator")
            results.append({"equals": actual == expected, "not_equals": actual != expected,
                            "contains": expected in actual if isinstance(actual, (str, list)) else False,
                            "not_contains": expected not in actual if isinstance(actual, (str, list)) else True,
                            "in": actual in expected if isinstance(expected, list) else False,
                            "not_in": actual not in expected if isinstance(expected, list) else True,
                            "is_empty": actual in (None, "", []), "is_not_empty": actual not in (None, "", []),
                            "greater_than": actual is not None and actual > expected,
                            "less_than": actual is not None and actual < expected}.get(operator, False))
        return all(results) if conditions.get("logic", "AND") == "AND" else any(results)

    @staticmethod
    def _apply(item: Case, action: dict[str, Any]) -> None:
        action_type, value = action.get("type"), action.get("value")
        if action_type == "set_field":
            field_code = action.get("field_code")
            value = action.get("value_id", action.get("value"))
            if field_code == "status": item.workflow_status_id = UUID(value)
            elif field_code == "priority": item.priority_id = UUID(value)
            elif field_code == "sub_priority": item.sub_priority_id = UUID(value)
            elif field_code == "assignee": item.assignee_id = UUID(value)
            elif field_code == "assignee_group": item.assigned_group_id = UUID(value)
            else: raise ValueError(f"Unsupported automation target field: {field_code}")
            return
        if action_type == "assign_user": item.assignee_id = UUID(value)
        elif action_type == "assign_group": item.assigned_group_id = UUID(value)
        elif action_type == "set_status": item.workflow_status_id = UUID(value)
        elif action_type == "set_priority": item.priority_id = UUID(value)
        elif action_type == "set_sub_priority": item.sub_priority_id = UUID(value)
        else: raise ValueError(f"Unsupported automation action: {action_type}")
