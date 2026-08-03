# Configurable case-management foundation

This draft adds the operational platform layer on the existing `feat/foundation-and-first-case-flow` branch.

## Included

- Alembic revisions through `0008`.
- Configurable workflow definitions, statuses, transitions, legal transition validation, history and audit.
- SLA policies with request-type/priority specificity and case response/resolution due dates.
- Secure local attachments with logical deletion and authorized download.
- In-app notification persistence and future delivery outbox.
- Hebrew Workflow and SLA environment tabs plus SLA and attachment case panels.
- New Hebrew permission catalog entries for workflow, SLA, attachments, notifications, audit and status history.

## Verification

- Backend: Ruff, mypy, Alembic upgrade/check and 31 tests.
- Frontend: ESLint, TypeScript, 17 tests and Vite production build.
- Browser: login and Workflow/SLA data verified at `http://localhost:3000/`, including persistence after service restart.

## Run locally

`powershell -ExecutionPolicy Bypass -File .\scripts\start-local.ps1`

Frontend: `http://localhost:3000/`  
Backend: `http://localhost:8000/`  
Database: `data/case_management.db`

## Remaining

The complete status/transition editor, notification center, full audit page, background SLA warnings, complete report filters, attachment-to-comment composer, and remaining bulk-permission scale/tri-state work are tracked in `docs/product/roadmap.md`.
