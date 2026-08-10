# Case Management

A flexible, configurable case management platform for service requests, operational workflows, approvals, and internal support processes.

> **Project status:** Active development / pre-release.
>
> The project is evolving quickly. APIs, configuration models, and UI flows may change before the first stable release.

## Overview

Case Management is designed to provide a reusable foundation for managing service requests across different business domains without hard-coding the application around a single help-desk process.

The core idea is simple: keep the platform stable, move business-specific behavior into controlled configuration, and make day-to-day use straightforward for both requesters and support teams.

The system currently focuses on:

- Multiple configurable work environments
- Service request / case lifecycle management
- Configurable request types, statuses, priorities, and sub-priorities
- Dynamic case fields and forms
- Workflow-based status transitions
- Public conversations and restricted manager notes
- Participants, assignees, locking, and controlled editing
- Approval workflows
- Permission-based access control
- Case reporting and filtering
- Attachments and audit history
- Hebrew and RTL-friendly user experience

## Product Principles

The project follows several design principles:

- **Simple for end users** — common actions should require as few steps as possible.
- **Configurable for administrators** — business behavior should be configurable without routine code changes.
- **Environment-aware** — each environment acts as a real configuration and security boundary.
- **Backend-authoritative security** — permissions are enforced by the API, not only by hidden UI controls.
- **No hard-coded business data** — request types, statuses, priorities, and other business values belong in configuration and the database.
- **Safe history** — values already used by historical cases should be deactivated or archived instead of destructively removed.
- **Regression protection** — every feature and bug fix must be covered by automated tests.

## Technology Stack

### Backend

- Python 3.12+
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- JWT authentication
- SQLite for local development
- Optional PostgreSQL support

### Frontend

- React 19
- TypeScript
- Vite
- Material UI
- TanStack Query
- React Hook Form
- Zod
- Vitest

## Architecture

The repository is organized as a small monorepo:

```text
case-management/
├── apps/
│   ├── api/               # FastAPI backend
│   └── web/               # React frontend
├── data/                  # Local runtime data (not committed)
├── docs/                  # Architecture, API and ADR documentation
├── scripts/               # Setup, start, stop and regression scripts
├── AGENTS.md               # Engineering and product rules
└── README.md
```

Architecture decisions and design documentation live under [`docs/`](docs/).

The API contract is maintained in:

```text
docs/api/API_SPEC.md
```

## Getting Started

### Prerequisites

For local Windows development:

- Windows 10/11
- Python 3.12+
- Node.js 22+
- npm
- Git

### First-time setup

Clone the repository and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-local.ps1
```

The setup script prepares the Python environment, installs backend and frontend dependencies, and applies the database migrations required for local development.

### Start the application

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-local.ps1
```

Local services:

| Service | Address |
|---|---|
| Web application | `http://localhost:3000` |
| API | `http://localhost:8000` |
| OpenAPI / Swagger | `http://localhost:8000/docs` |
| Health check | `http://localhost:8000/health` |

### Stop the application

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\stop-local.ps1
```

> Do not open `apps/web/index.html` directly. The frontend is a Vite application and must run through the development server.

## Local Data

Local development uses SQLite by default.

Runtime database files, uploaded attachments, branding assets, secrets, and other environment-specific data must not be committed to Git.

The local database is intended to persist between restarts. Database schema changes are managed through Alembic migrations.

## Users and Authentication

The application supports local authentication and is being designed to support multiple user provisioning models, including:

- Manual user management
- Spreadsheet import/export
- Microsoft Entra ID / Active Directory synchronization

Development fixtures and automated-test identities are not production credentials and should never be reused in deployed environments.

No production secrets, passwords, tokens, tenant credentials, or private environment configuration should be committed to this repository.

## Permissions

Authorization is enforced on the backend.

The target permission model uses:

- User groups for permission inheritance
- User-level overrides
- Environment-specific permission overrides
- Environment membership for access scope

Organizational attributes such as department and job title are treated as user data, not as permission roles.

## Testing

Regression protection is a core project requirement.

Run the canonical test suite from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-regression.ps1
```

The regression runner is expected to validate the relevant combination of:

- API contract tests
- Backend tests
- Permission behavior
- Frontend tests
- Type checking
- Linting
- Production build

A feature or bug fix is not considered complete when the regression suite fails.

### Backend tests

Backend tooling includes:

- `pytest`
- `ruff`
- `mypy`
- Alembic migration checks

### Frontend tests

Frontend tooling includes:

- `vitest`
- ESLint
- TypeScript type checking
- Vite production build

## API Documentation

During local development, interactive OpenAPI documentation is available at:

```text
http://localhost:8000/docs
```

The maintained project-level API contract is available at:

[`docs/api/API_SPEC.md`](docs/api/API_SPEC.md)

## Security

This repository should never contain:

- Real user passwords
- API keys or access tokens
- Microsoft Entra / Active Directory secrets
- Production `.env` files
- Local SQLite databases
- User-uploaded attachments
- Company branding files containing sensitive information

If you discover a security issue, please avoid publishing sensitive details in a public issue. A dedicated security policy should be added before the first public release.

## Development Guidelines

Engineering and product rules are documented in [`AGENTS.md`](AGENTS.md).

Important expectations include:

- Keep modules reasonably small and focused
- Prefer configuration over hard-coded business behavior
- Enforce permissions server-side
- Preserve historical data safely
- Update the API contract when behavior changes
- Add regression coverage for every meaningful feature or bug fix
- Verify frontend and backend behavior together

## Roadmap

Current and planned areas include:

- Improved user and group management
- Manual, Excel, Microsoft Entra ID, and Active Directory user provisioning
- Department/job-title based environment assignment
- Approval routing by organizational attributes
- Richer workflow configuration
- Reporting and operational dashboards
- Branding and deployment configuration
- Additional automation capabilities
- PostgreSQL deployment path
- Expanded API and integration support

Roadmap items are subject to change while the project remains pre-release.

## Contributing

Contributions will be welcome once the repository is prepared for public collaboration.

Before opening the project publicly, the repository should include dedicated:

- `CONTRIBUTING.md`
- `SECURITY.md`
- Issue / pull request templates
- Code of Conduct, if community contribution is expected

Until those files are added, please treat the repository as an actively evolving development project.

## License

A public open-source license has not yet been selected.

Before the repository is made public for reuse or external contribution, an explicit `LICENSE` file should be added so that usage, modification, and redistribution terms are unambiguous.
