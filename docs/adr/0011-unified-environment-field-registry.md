# ADR 0011: Unified environment field registry

## Status

Accepted

## Context

Environment administration, automation and approvals previously exposed separate lists and technical values. This made the same case field behave differently between configuration screens and encouraged automation rules to depend on labels.

## Decision

- Define one backend registry for core case fields and expose discovery and option endpoints scoped to an environment.
- Persist references in automation conditions and actions by stable field code and entity UUID, never by the Hebrew display label.
- Treat sub-priority as an environment-managed value independent of priority while retaining the nullable legacy relation during migration.
- Bind approval configuration to request type, snapshot its policy on each approval instance, and version a flow after it has been used.
- Keep Hebrew labels as editable presentation metadata and retain generated technical identifiers as immutable integration details.

## Consequences

Administration and rule builders consume the same vocabulary and option sources. Renaming a label does not invalidate existing rules. Existing sub-priority rows remain usable after migration. Approval instances remain auditable when administrators edit a flow later.
