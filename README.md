# Case Management

Generic, RTL-first case-management and workflow platform implemented as a modular monolith.

## Architecture

- React 19 + TypeScript + Vite frontend
- FastAPI + SQLAlchemy 2 + PostgreSQL backend
- Versioned dynamic forms with typed case-field values
- JWT authentication and backend-enforced RBAC
- MinIO object storage and Mailpit development mail server

See `docs/architecture/overview.md` and `docs/adr/` for the design record.

## Prerequisites and startup

Install Docker Desktop, then copy `.env.example` to `.env` and run:

```powershell
docker compose up --build
```

The API applies Alembic migrations and development seed data on startup. Seed passwords are **development-only**.

| Service | URL |
|---|---|
| Web app | http://localhost:3000 |
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| MinIO console | http://localhost:9001 |
| Mailpit | http://localhost:8025 |

Development users: `admin@example.com` / `Admin123!`, `requester@example.com` / `Requester123!`, and `agent@example.com` / `Agent123!`.

Stop with `docker compose down`; remove local development volumes with `docker compose down -v`.

## Development commands

```powershell
# Backend
cd apps/api
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
.venv\Scripts\alembic upgrade head
.venv\Scripts\pytest
.venv\Scripts\ruff check .
.venv\Scripts\mypy app

# Frontend
cd apps/web
npm install
npm run lint
npm run typecheck
npm test
npm run build
```

Create a migration with `alembic revision --autogenerate -m "description"`; validate with `alembic upgrade head`.

## Repository layout

- `apps/api`: FastAPI application, migrations, seed and tests
- `apps/web`: responsive RTL React application
- `docs`: architecture, product notes and ADRs
- `infrastructure`: container configuration
- `scripts`: Windows-friendly operational helpers
- `.github/workflows`: pull-request CI

Future roadmap: configurable workflow/approvals, automation, notifications, reporting, SLA, and integrations.
