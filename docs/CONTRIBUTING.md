# Contributing / handoff guide

This portal is handed to ECE maintainers who may not have built the original stack. Use this page as the entry point.

## Where to start

1. Root [README.md](../README.md) — stack, local run, module route table
2. [ARCHITECTURE.md](ARCHITECTURE.md) — system shape
3. [MODULES.md](MODULES.md) — feature-by-feature behavior
4. [DEVELOPMENT.md](DEVELOPMENT.md) — how to add an API/UI change safely
5. [FILE_INVENTORY.md](FILE_INVENTORY.md) — every tracked file with a one-line purpose (regenerate with the script below)
6. [DATABASE.md](DATABASE.md) — schema / Alembic policy
7. [CONFIGURATION.md](CONFIGURATION.md) — environment variables
8. [TESTING.md](TESTING.md) — how to verify changes
9. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — common production failures
10. [BACKUP_RESTORE.md](BACKUP_RESTORE.md) — dump / restore checklist

## Golden rules

- **MySQL is the source of truth.** CSVs under `data/assets/` are synced mirrors for some modules; do not edit only one side.
- **Schema changes go through Alembic.** Do not rely on `Base.metadata.create_all()` alone in production (it creates missing tables but does not alter columns).
- **Faculty-scoped data** uses `FacultyScope` in `backend/app/auth/dependencies.py`. Non-admins must only see their linked `users.faculty_id`.
- **Publications deleted in the UI are tombstoned** in `blocked_publications` so Scholar sync cannot re-insert them.
- **Do not commit secrets.** `backend/.env`, `.env.docker`, and `data/assets/` are local/runtime.

## Regenerating the file inventory

```powershell
cd backend
python scripts/generate_file_inventory.py
```

This rewrites `docs/FILE_INVENTORY.md`. Commit the regenerated file with structural changes.
