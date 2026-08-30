# Legacy Case Flow Audit

## ACTIVE — canonical runtime

- `GlobalFieldDefinition` and `CaseFieldValue`, addressed by stable IDs.
- `semantic_binding` values `case.status`, `case.priority`, `case.sub_priority`, and
  `case.assignee` through `CaseSemanticFieldService`.
- Case Details global-field controls, Dashboard, reports, filters, transfer, bulk status,
  parent/child status, export, and API DTO display values.
- `Case.workflow_status_id`, `priority_id`, `sub_priority_id`, and `assignee_id` only as
  synchronized query indexes written by the semantic service.

## LEGACY HISTORY ONLY — retained for compatibility

- `WorkflowDefinition`, `WorkflowStatus`, `WorkflowTransition`, `PriorityDefinition`, and
  `SubPriorityDefinition` tables are retained to read existing databases and historical audit data.
- Legacy catalog endpoints remain temporarily API-compatible for existing integrations and
  migration tooling; they are not linked from the active administration or Case Details UI.
- `CaseStatusHistory` remains the append-only status transition history.

These compatibility objects must not become an independent display or editing source for a Case
business value. New consumers must use `CaseSemanticFieldService`.

## SAFE TO REMOVE — removed

- The legacy Workflow Status selector beside Request Type in Case Details.
- Its duplicate status-options query and cascade-dialog wiring.
- The unreferenced environment `WorkflowsTab` administration component.
- The unreferenced legacy `CasesPage` with hardcoded English lifecycle values.

The permanent frontend regression test rejects reintroduction of the legacy Case Details status
editor while requiring the configurable global-field editing surface.
