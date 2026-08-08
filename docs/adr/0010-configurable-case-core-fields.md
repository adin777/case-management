# ADR 0010: Configurable case core fields

## Status

Accepted — 2026-08-08.

## Decision

Every case permanently owns the core fields environment, request type, title, description, workflow status, priority, and sub-priority. Title, description, and environment are required. Workflow status is resolved from the active workflow assigned to the request type (or the environment default workflow), and creation is blocked when there is no active initial status.

`workflow_status_id`, `priority_id`, and `sub_priority_id` are the business sources of truth. Labels come from their definitions. The legacy `cases.status` enum and `cases.priority` code remain populated only for backward compatibility with historical rows and older report consumers; they do not define available values or transitions. Status changes are validated exclusively against `WorkflowTransition` and recorded in `CaseStatusHistory`.

Startup runs migrations and the technical foundation bootstrap before opening either server. The bootstrap may create or repair only the system administrator, base groups, technical permissions, roles, and permission domains. Business environments, request types, forms, priorities, workflows, statuses, transitions, SLA policies, and demo users are never created by normal startup.

## Consequences

- A missing workflow or initial status is a visible configuration error, not a hidden fallback.
- Fresh installations contain no invented business taxonomy.
- Removing the legacy columns requires a later migration after all report and integration consumers use definition identifiers.
