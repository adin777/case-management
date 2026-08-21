# ADR 0010: Configurable case core fields

## Status

Accepted — 2026-08-08.

## Decision

Every case permanently owns the core fields environment, request type, title, description, workflow status, priority, and sub-priority. Title, description, and environment are required. Workflow status is resolved from the active workflow assigned to the request type (or the environment default workflow), and creation is blocked when there is no active initial status.

When an active Global Field has a semantic binding, its `GlobalCaseFieldValue` is the business source of truth. `workflow_status_id`, `priority_id`, `sub_priority_id`, and `assignee_id` are synchronized query indexes owned by `CaseSemanticFieldService`; consumers must not write them independently. Labels come from the bound value definition. The legacy `cases.status` enum and `cases.priority` code remain populated only for backward compatibility and do not define available values or transitions. Status changes are recorded in `CaseStatusHistory`.

Startup runs migrations and the technical foundation bootstrap before opening either server. The bootstrap may create or repair only the system administrator, base groups, technical permissions, roles, and permission domains. Business environments, request types, forms, priorities, workflows, statuses, transitions, SLA policies, and demo users are never created by normal startup.

## Consequences

- A missing workflow or initial status is a visible configuration error, not a hidden fallback.
- Fresh installations contain no invented business taxonomy.
- Removing the legacy columns requires a later migration after all report and integration consumers use definition identifiers.
