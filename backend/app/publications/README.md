# Publications Module Setup

## Backend dependencies

Install or update backend dependencies:

```bash
pip install -r backend/requirements.txt
```

## Migration

Run Alembic migration:

```bash
cd backend
alembic upgrade head
```

## Environment variables

The module uses `MYSQL_*` / `DATABASE_URL` from `backend/.env`.

| Variable | Purpose |
|----------|---------|
| `ENABLE_SCHEDULER` | `true` to run **monthly publication gap-fill** (1st of month). Does not control notification reminders. |
| `SERP_API_KEY`, `SCRAPER_BACKEND` | Publication scraping |

See [docs/MAINTENANCE.md](../../../docs/MAINTENANCE.md) for sync operations.

## CSV import

Faculty CSV must include columns:

- `id`
- `name`
- `designation`
- `department`
- `scholar_id`
- `join_year`
- `leave_year`
- `photo_url`
- `profile_link`

Scholar IDs must be true Google Scholar user IDs, e.g. `abc123XYZ`.
