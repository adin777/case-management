# ADR 0009: Business access levels and durable approval state

## Status

Accepted — 2026-08-03.

## Context

Administrators need a Hebrew, business-oriented permission model instead of assigning dozens of technical permission codes. Approval flows also need an explicit case-level outcome that remains visible after the individual tasks are completed.

## Decision

The platform exposes named permission domains with three levels: none, view, and edit. Assignments may target users or groups and may be system-wide or environment-specific. Each domain maps to existing technical permission codes, so authorization remains enforced by the backend. Explicit technical denies continue to override derived access.

Bulk assignment and permission copying are audited. Copying supports full replacement, merge, and filling missing domains only.

Approval instances update durable fields on the case (`approval_status`, `is_approved`, approval time, and approver summary). Approval tasks are created per step and notify approvers; terminal decisions notify the requester. Rejection and return require a comment.

## Consequences

- The administrative UI can remain stable while technical permissions evolve.
- Existing role and explicit permission mechanisms remain compatible.
- Historical audit rows retain actor snapshots when development identities are removed.
- Any future permission domain must define its technical view/edit mapping and be covered by authorization tests.
