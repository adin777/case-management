# ADR 0004: Configurable platform services and effective permissions

Date: 2026-08-02

## Status

Accepted

## Context

The product needs environment-scoped request configuration, stable human-readable identifiers, direct permissions, automation, reporting, and sequential approval flows while retaining the existing SQLite database and monolith deployment.

## Decision

- Allocate human-readable identifiers through a central `NumberingService` backed by `numbering_series`. Allocation occurs in the same database transaction as the created entity. Prefixes identify entity families and counters are scoped globally or by environment.
- Calculate effective permissions from system-administrator status, role grants, group grants, direct group assignments, and direct user assignments. System administrators receive the full catalog. For every other user, an explicit deny overrides any allow at the same system/environment lookup.
- Execute automation only in the backend through `AutomationEngine`. Persist every evaluation, including unmatched and failed rules, and cap a single chain at 20 actions.
- Keep approval definitions separate from runtime instances and tasks. Runtime decisions are authorized against the assigned approver and recorded in the audit log.
- Generate reports with server-side filtering, sorting, authorization, and pagination. Excel export reuses the same authorized query and emits a real OOXML workbook.

## Consequences

Configuration is auditable and portable without exposing UUIDs as business identifiers. Permission conflicts are deterministic. SQLite remains supported, though row locking is necessarily weaker than on PostgreSQL; the unique indexes remain the final duplicate-number safeguard. Automation and approval actions can be expanded behind their service boundaries without moving to microservices.
