# ADR-006: SQLite for local development

Status: Accepted.

Local Windows development uses a persistent SQLite database under `data/case_management.db` so the product can run without Docker or PostgreSQL. SQLAlchemy models use portable types and business logic contains no SQLite-specific SQL. Connection setup enables foreign keys and WAL. PostgreSQL remains an optional deployment target through the `postgres` dependency extra.

This supersedes ADR-002 only for the local database engine; the typed dynamic-field model remains unchanged.
