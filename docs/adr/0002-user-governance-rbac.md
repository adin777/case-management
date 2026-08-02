# ADR 0002: Explicit environment-scoped RBAC and separated collaboration feeds

## Status

Accepted — 2026-08-02

## Context

Case access and administrative behavior previously depended on a small JSON permission list attached to a direct environment membership. Group-derived access and the distinction between public conversation and manager-only communication were incomplete.

## Decision

- Keep the application as a modular monolith and introduce a dedicated `governance` domain router.
- Store a normalized permission catalog and role-permission assignments while retaining the legacy role JSON column during migration for backwards compatibility.
- Resolve effective environment permissions as the union of direct environment roles and group environment roles. System administrators bypass environment scope and receive the complete catalog.
- Treat case ownership, participation and environment-wide permission as separate access sources.
- Expose public and manager conversations through separate endpoints. Manager messages require explicit `comment.manager.read` or `comment.manager.create`; the agent role does not receive these permissions.
- Keep the legacy textual priority column during safe data transition and add foreign keys to configurable priority and sub-priority definitions.

## Consequences

Backend permission checks remain the source of truth and UI capabilities are derived from the case response. Existing SQLite data remains readable, while new cases use configured priority identifiers. A later migration may remove the compatibility JSON and textual priority columns after all production-like data has been backfilled and verified.
