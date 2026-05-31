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

The module uses existing `DATABASE_URL`/`database_url` and scheduler lifecycle.
Optional scraping settings can be added later if needed:

- `PUBLICATIONS_SCRAPE_DELAY_MIN_SECONDS` (default behavior uses 3)
- `PUBLICATIONS_SCRAPE_DELAY_MAX_SECONDS` (default behavior uses 8)

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
