# Codex working agreement

- Never change the database schema without an Alembic migration.
- Do not add a dependency without a concrete product or engineering justification.
- Never bypass backend authorization or persist secrets.
- Do not delete data without explicit approval.
- Run relevant tests before committing and push completed meaningful work.
- Record material architectural decisions in `docs/adr`.
