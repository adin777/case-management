# ADR 0003: Structured dynamic user-field configuration

## Status

Accepted — 2026-08-02

## Context

User-field definitions need type-specific validation, stable select-option identities, and optional visibility in multiple environments. Storing display text as an option identity would make future label edits unsafe, while creating the field and its environment links in separate operations could leave partial configuration behind.

## Decision

- Select options are stored as structured objects containing an opaque UUID value, Hebrew and English labels, active state, and sort order.
- The administration UI accepts a simple comma-separated Hebrew list and normalizes it before producing the structured representation.
- Non-select field types always persist an empty options array.
- User-field creation and environment-link creation run in one database transaction after all selected environments have been validated as active.
- Existing field types may change only while the field has no stored user values.
- Group names are unique case-insensitively, enforced by migration `0003` and accompanied by a domain-specific conflict response.

## Consequences

Option labels can change without invalidating saved values, environment assignments cannot be partially applied, and both frontend and backend enforce the same field-type invariants. SQLite cannot reflect expression indexes during Alembic autogeneration, so `alembic check` emits a known reflection warning while reporting no pending operations.
