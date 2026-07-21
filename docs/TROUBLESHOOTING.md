# Troubleshooting

## Backend will not start

- Check MySQL is reachable with `MYSQL_*` from `.env`.
- Run `alembic upgrade head` — missing tables/columns often look like random 500s.
- In production, weak `SECRET_KEY` or `DEBUG=true` can abort startup intentionally.

## Frontend shows "Something went wrong. Please try again."

The UI sanitizes large/HTML 500 bodies in `frontend/src/services/api.ts`. Check backend logs (Gunicorn/Uvicorn or `docker compose logs api`) for the real traceback. Common causes: missing LLM, SerpAPI errors, DB schema drift, null faculty scope.

## Publications sync adds nothing / fails

- Confirm `SERP_API_KEYS` and `SCRAPER_BACKEND=serpapi`.
- Open **Publications Admin → Scrape Logs**.
- Deleted papers are skipped if their `source_hash` is in `blocked_publications` (expected).
- Links containing `repository.iiitd.edu.in` are rejected by design.

## Faculty cannot edit/delete publications

- Their `users.faculty_id` must point at the correct `faculty.id` row (migration 034 / Admin Users linking).
- They can only manage publications linked through `publication_faculty`.

## SDG generate fails only on server

- Confirm Ollama is reachable from the API host (`LOCAL_LLM_BASE_URL`).
- In Docker, Ollama usually runs on the host → `http://host.docker.internal:11434/v1`.
- Check project SDG queue / background thread exceptions in API logs.

## Student Excel import fails

- File must be `.xlsx`/`.xls` with Title, Authors, and Years/Year columns (aliases accepted).
- Extra columns are stored in `extra_fields` JSON and shown dynamically.

## Course allocation views disagree

Both views read the same allocation tables/CSV sync. After admin CRUD, hard-refresh both pages. If CSV mirrors exist, confirm `DATA_ASSETS` path is writable on the server.
