# Backup and restore

## What to back up

1. **MySQL database** (required) — all portal state.
2. **`data/assets/`** — CSV/Excel mirrors and templates (gitignored).
3. **`storage/`** — uploaded files, generated exports, document blobs.
4. **`backend/documents/`** — meeting PDF trees if used outside DB storage.
5. **Env files** — `backend/.env` / `.env.docker` stored securely offline (never in Git).

## MySQL dump (example)

```bash
mysqldump -u USER -p DATABASE > ece_portal_$(date +%F).sql
```

Restore:

```bash
mysql -u USER -p DATABASE < ece_portal_YYYY-MM-DD.sql
cd backend && alembic upgrade head
```

After restore, confirm `alembic current` matches the code revision you deployed.

## Docker volume note

Compose setups usually persist MySQL and bind-mount `data/assets` + `storage`. Back up those volumes/bind mounts with the SQL dump.

## Verification after restore

1. `/health` returns ok.
2. Admin login works.
3. Faculty directory counts look sane.
4. Spot-check one CO-PO result, one project, one allocation semester.
5. Open a meeting minutes document that has an attachment.
