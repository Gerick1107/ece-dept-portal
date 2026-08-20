# Troubleshooting

## Backend will not start

- Check MySQL is reachable with `MYSQL_*` from `.env`.
- Run `alembic upgrade head` — missing tables/columns often look like random 500s.
- In production, weak `SECRET_KEY` or `DEBUG=true` can abort startup intentionally.
- **Always** pass `--env-file .env.docker` (e.g. `docker compose --env-file .env.docker logs -f`). Without it, Compose errors with `SECRET_KEY` / `BOOTSTRAP_ADMIN_PASSWORD` missing even when the file is fine. See the up/down cheat sheet in [SETUP.md](SETUP.md) §A6.
- Keep `SECRET_KEY=…` on **one line** in `.env.docker`. Soft-wrapped hex (second line of digits) truncates the key.

## MySQL container unhealthy / “dependency failed to start”

Backend will not start until MySQL is healthy — so **bootstrap admin is not created** either. Inspect MySQL:

```bash
docker compose --env-file .env.docker ps
docker compose --env-file .env.docker logs mysql
```

Common causes: bad/mismatched `MYSQL_*` passwords, port conflict on `3307`, disk/memory pressure, or a half-initialized volume after a failed first start (`down -v` only if you accept wiping DB data).

## Frontend shows "Something went wrong. Please try again."

The UI sanitizes large/HTML 500 bodies in `frontend/src/services/api.ts`. Check backend logs (Gunicorn/Uvicorn or `docker compose logs api`) for the real traceback. Common causes: missing LLM, SerpAPI errors, DB schema drift, null faculty scope.

## Publications sync adds nothing / fails

- Confirm `SERP_API_KEYS` and `SCRAPER_BACKEND=serpapi`.
- Open **Publications Admin → Scrape Logs**.
- Deleted papers are skipped if their `source_hash` is in `blocked_publications` (expected).
- Links containing `repository.iiitd.edu.in` are rejected by design.

## CO-PO: mapping file not found

`data/assets/` is **gitignored**. Copy `default_mapping.xlsx` (and other assets) onto the server — see [DATA_ASSETS.md](DATA_ASSETS.md). The red banner is expected on a bare clone.

## LLM: model not pulled / offline

Warnings name whatever is in `LOCAL_LLM_MODEL` (not a hard-coded model). With the compose Ollama stack:

```bash
docker compose -f docker-compose.ollama.yml --env-file .env.docker up -d
docker compose -f docker-compose.ollama.yml --env-file .env.docker logs ollama-pull
```

First pull can take several minutes. For a remote Ollama host, set `LOCAL_LLM_BASE_URL` / `LOCAL_LLM_MODEL` in `.env.docker` — see [CONFIGURATION.md](CONFIGURATION.md#local-llm-ollama).

## Faculty cannot edit/delete publications

- Their `users.faculty_id` must point at the correct `faculty.id` row (migration 034 / Admin Users linking).
- They can only manage publications linked through `publication_faculty`.

## SDG generate fails only on server

- Confirm Ollama is reachable from the API host (`LOCAL_LLM_BASE_URL`).
- **Host Ollama:** In Docker, use `http://host.docker.internal:11434/v1` and `LOCAL_LLM_MTLS_ENABLED=false`.
- **Compose Ollama:** Start `docker-compose.ollama.yml`, set `LOCAL_LLM_BASE_URL=https://ollama-proxy:8443/v1` and `LOCAL_LLM_MTLS_ENABLED=true` (certs via `scripts/generate_mtls_certs.*`). Both stacks must share the `portal-shared` network.
- See [SETUP.md](SETUP.md) for the dual-compose flow.
- Check project SDG queue / background thread exceptions in API logs.

## Student Excel import fails

- File must be `.xlsx`/`.xls` with Title, Authors, and Years/Year columns (aliases accepted).
- Extra columns are stored in `extra_fields` JSON and shown dynamically.

## Course allocation views disagree

Both views read the same allocation tables/CSV sync. After admin CRUD, hard-refresh both pages. If CSV mirrors exist, confirm `DATA_ASSETS` path is writable on the server.
