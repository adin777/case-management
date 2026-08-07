# ADR 0007: Operational workflow, SLA, and local attachments

## Status

Accepted — 2026-08-03

## Context

The local product needs configurable workflows, SLA targets, attachments, notifications, and auditability while preserving the existing SQLite database and keeping a future PostgreSQL deployment viable.

## Decision

- Keep the legacy case status column during migration and add a workflow-status reference as the configurable source of operational state.
- Resolve SLA policies deterministically by request type and priority specificity, using calendar minutes for the local phase while retaining a future business-calendar identifier.
- Store attachment metadata in the database and bytes below `data/attachments`, using generated storage names, MIME allow-listing, a configurable 10 MB default limit, SHA-256, authorization on every read, and logical deletion.
- Add `python-multipart` because standards-compliant browser file uploads to FastAPI require multipart parsing; no storage or cloud dependency is introduced.
- Persist in-app notifications and an outbox record model so an email adapter can be added later without credentials or synchronous external delivery in request handlers.
- Keep the operational entities in a separate module and register its metadata explicitly with Alembic.

## Consequences

The migration is portable and existing case data remains readable. During the compatibility period, code must avoid treating the legacy enum as the configurable workflow source. Local file storage is intentionally single-node and must be replaced behind the same service boundary before distributed deployment.
