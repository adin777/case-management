# ADR 0012: Semantic case workspace and safe configuration lifecycle

## Status

Accepted.

## Decision

Workflow statuses carry a stable `semantic_category` (`open`, `in_progress`, `waiting`, `resolved`, or `closed`). Dashboard activity filters use that category rather than localized labels. Case creation obtains environments from a dedicated authorization-aware endpoint that returns active memberships only, while historical case reads retain inactive environments.

Priority and sub-priority deletion is physical only after an explicit server-side dependency check across cases, request-type defaults, automation configuration, SLA policies, and dependent values. Referenced values return a Hebrew `409 Conflict` and remain available for deactivation. Deletion writes an audit event and never cascades.

Legacy demo fields (`location`, `device_type`, `details`, and the discovered `urgency`) with historical values are retained in storage but marked inactive through migration. Active create, detail, and edit views render only active fields; editing additionally excludes read-only fields.

## Consequences

- Display labels can change without altering dashboard activity semantics.
- Inactive configuration remains readable in historical records.
- Configuration removal is predictable and does not cause silent data loss.
- SQLite and future PostgreSQL implementations share the same domain behavior without relying on localized strings.
