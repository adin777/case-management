# Architecture overview

The system is a modular monolith: one deployable API and one PostgreSQL database, with domain ownership separated under `app/modules`. Modules communicate through explicit services rather than network calls. This keeps the first release operable while preserving boundaries for later extraction if scale demands it.

Initial domains are identity/users, authorization, environments, request types/forms, cases, comments/participants, and audit. Attachments are designed to use MinIO but are not in the first vertical slice. Workflow, approvals, automation, notifications, reports, SLA and integrations are roadmap capabilities, not placeholder code.

Every protected operation is authorized in the API. Environment membership scopes access; system administrators bypass membership checks. Dynamic form definitions are immutable after publication and each case points to the exact published version used at creation.
