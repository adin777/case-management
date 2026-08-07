# ADR 0005: Bulk permissions and persistent case locking

## Status

Accepted

## Context

Administrators need to apply multiple permissions to multiple users or groups in one operation. Case managers also need to prevent normal edits while retaining the public conversation. Both controls must be enforced by the API and audited rather than relying on UI state.

## Decision

- Bulk permission operations use transactional `add`, `remove`, and `replace` endpoints for users and groups.
- Permission scope is validated server-side: system permissions require a system administrator and environment permissions require an environment identifier and management permission.
- Case lock state is persisted on the case with actor, timestamp and reason.
- A locked case rejects updates from ordinary editors with HTTP 423. Users who hold `case.lock` may edit and unlock it; comments remain available according to their own permissions.
- Updates retain optimistic concurrency through the existing case version field.

## Consequences

Permission administration is efficient and auditable, and lock behavior is consistent across every client. The permission and case tables gain explicit active/lock columns through Alembic revision `0005`.
