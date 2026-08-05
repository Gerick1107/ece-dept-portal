# Docker deployment (institute server)

When the portal is feature-complete, deploy with **two Compose files**:

| File | Stack |
|------|--------|
| `docker-compose.yml` | MySQL + backend + frontend (`portal-app` + `portal-shared` networks) |
| `docker-compose.ollama.yml` | Ollama + mTLS nginx proxy (`portal-shared` only) |
| `ops/backup/docker-compose.backup.yml` | Encrypted restic backups (optional ops) |

This pins Python 3.11, Node 20, and MySQL 8.0 so host Python/Node upgrades cannot break the portal.

Full start-to-finish: [SETUP.md](SETUP.md). Backups: [BACKUP_RESTORE.md](BACKUP_RESTORE.md).

## Prerequisites

- Docker Engine 24+ and Docker Compose v2
- Git clone of this repository on the server
- `data/assets/` populated locally (see [DATA_ASSETS.md](DATA_ASSETS.md)) — **not in Git**

## Collaborating before final deployment

If two developers want to use Docker **now** (not only on the institute server) while the portal is still in progress:

1. **Same Git branch** — Pull from the same remote branch often (`main` or a shared feature branch). Commit and push frequently so you do not diverge.

2. **Database** — One person maintains the canonical MySQL dump. The other imports it when schema or seed data changes:
   ```bash
   docker compose --env-file .env.docker exec -T mysql mysql -u portal_user -p"$MYSQL_PASSWORD" ece_dept_portal < dump.sql
   ```
   After pulling new code, run migrations on the shared Docker DB:
   ```bash
   docker compose --env-file .env.docker exec backend alembic upgrade head
   ```

3. **Shared `.env.docker`** — Agree on passwords and `SECRET_KEY` out of band (not in Git). Each machine copies `.env.docker.example` and uses the same values if you need identical JWT/login behaviour.

4. **CSV assets** — Share `data/assets/` out of band (secure copy or restore from SQL dump). Do not commit to Git. Mount into Docker on each host.

5. **Local ports** — Default UI is `http://localhost:8080`. If both run Docker on one machine, only one stack can bind the port; use different `PORTAL_HTTP_PORT` in `.env.docker` per developer.

6. **Do not commit** — `.env.docker`, SQL dumps with real credentials, `data/assets/`, or `storage/` uploads.

## Quick start

```bash
cd /opt/automation-portal   # or your clone path
cp .env.docker.example .env.docker
# Edit .env.docker — see “Variables you must change” below

docker compose --env-file .env.docker up -d --build
```

Open `http://<server>:8080` (or the port set in `PORTAL_HTTP_PORT`).

### Default bootstrap admin

Created on first API startup **only if no admin user exists yet**:

```env
BOOTSTRAP_ADMIN_EMAIL=admin@ece.iiitd.ac.in
BOOTSTRAP_ADMIN_PASSWORD=ChangeMeOnFirstLogin!
```

**Change the password immediately after first login.** If login fails with these values, an admin was likely created earlier with a different password — use User Management, forgot-password (SMTP), or `backend/scripts/reset_admin_password.py`.

### Variables you must change in `.env.docker`

Copy from `.env.docker.example`. **Never commit** the filled file.

| Variable | Required? | Notes |
|----------|-----------|--------|
| `MYSQL_ROOT_PASSWORD` | Yes | Strong password for MySQL root |
| `MYSQL_PASSWORD` | Yes | Strong password for `portal_user` |
| `SECRET_KEY` | Yes | `openssl rand -hex 32` |
| `BOOTSTRAP_ADMIN_EMAIL` | Yes | Default `admin@ece.iiitd.ac.in` |
| `BOOTSTRAP_ADMIN_PASSWORD` | Yes | Default `ChangeMeOnFirstLogin!` |
| `PORTAL_FRONTEND_URL` | Yes | Public URL of the portal |
| `CORS_ORIGINS` | Yes | Must match the browser origin(s) |
| `SERP_API_KEYS` | For scraping | Comma-separated keys — see [CONFIGURATION.md](CONFIGURATION.md#serpapi-keys) |
| `SERP_API_KEY` | Fallback only | Used only if `SERP_API_KEYS` is empty |
| `SCRAPER_BACKEND` | Docker | Keep `serpapi` |
| `SMTP_*` | Recommended | Enable for password reset / reminders |

### Backup env files (`ops/backup/`)

These are **separate** from `.env.docker`:

| File | Copy from | Change |
|------|-----------|--------|
| `bac.env` | `bac.env.example` | `RESTIC_PASSWORD`, `BACKUP_TARGET_PATH`, schedule |
| `db.env` | `db.env.example` | `MYSQL_PASSWORD` / `MYSQL_ROOT_PASSWORD` = same as `.env.docker` |

Details: [BACKUP_RESTORE.md](BACKUP_RESTORE.md).

## Services

| Service | Role |
|---------|------|
| `mysql` | MySQL 8.0 database (persistent volume `mysql_data`) |
| `backend` | FastAPI on port 8000 (internal); runs `alembic upgrade head` on start |
| `frontend` | Nginx serving the React build; proxies `/api/` to backend |
| `ollama` + `ollama-proxy` | Optional LLM stack (`docker-compose.ollama.yml`) on `portal-shared` |
| `backup` | Optional restic loop (`ops/backup/`) |

### Networks

| Network | Purpose |
|---------|---------|
| `portal-app` | mysql ↔ backend ↔ frontend |
| `portal-shared` | backend ↔ ollama-proxy (mTLS) / ollama |

### Ollama modes

1. **Host Ollama** (testing): `LOCAL_LLM_BASE_URL=http://host.docker.internal:11434/v1`, `LOCAL_LLM_MTLS_ENABLED=false`
2. **Compose Ollama + mTLS** (institute): generate certs, start `docker-compose.ollama.yml`, set `LOCAL_LLM_BASE_URL=https://ollama-proxy:8443/v1` and `LOCAL_LLM_MTLS_ENABLED=true`

## Environment variables (backend / `.env.docker`)

| Variable | Default | Purpose |
|----------|---------|---------|
| `ENABLE_REQUIREMENT_REMINDERS` | `true` | Requirement reminder background job |
| `REQUIREMENT_REMINDER_POLL_MINUTES` | `1` | How often due reminders are checked |
| `ENABLE_SCHEDULER` | `false` | Monthly publication gap-fill only |
| `SMTP_ENABLED` | `false` | Required for email reminders in production |
| `LOCAL_LLM_MTLS_ENABLED` | `false` | Client certs for ollama-proxy |
| `SERP_API_KEYS` | _(empty)_ | Preferred: comma-separated SerpAPI keys for Scholar scrape |
| `SERP_API_KEY` | _(empty)_ | Single-key fallback if `SERP_API_KEYS` is unset |

## Production hardening checklist

Before IT security review / institute handoff:

1. Set strong `SECRET_KEY` (`openssl rand -hex 32`) in `.env.docker`
2. Set strong `MYSQL_ROOT_PASSWORD` and `MYSQL_PASSWORD`
3. Set `APP_ENV=production` and `DEBUG=false` (already in compose)
4. Set `PORTAL_FRONTEND_URL` and `CORS_ORIGINS` to the real HTTPS URL
5. Put **TLS** in front (institute reverse proxy / load balancer terminating HTTPS)
6. Restrict MySQL port — do **not** publish 3306 to the internet (compose binds `127.0.0.1:3307` only)
7. Enable SMTP for password reset emails if required
8. Set `SERP_API_KEYS` (comma-separated) for publications scraping — [CONFIGURATION.md](CONFIGURATION.md#serpapi-keys)
9. Enable restic backups ([BACKUP_RESTORE.md](BACKUP_RESTORE.md)) — fill `bac.env` + `db.env`
10. Prefer mTLS Ollama on servers that do not already trust the host network
11. Change bootstrap admin password after first login (`ChangeMeOnFirstLogin!` → a strong password)
12. Review [SECURITY.md](SECURITY.md)

## Useful commands

```bash
# View logs
docker compose --env-file .env.docker logs -f backend

# Rebuild after code updates
docker compose --env-file .env.docker up -d --build

# Stop
docker compose --env-file .env.docker down

# Stop and remove DB volume (destructive)
docker compose --env-file .env.docker down -v
```

## Optional: MySQL only in Docker

For local Windows dev with native Python, keep using host MySQL on port 3306. Optional containerized MySQL on port 3307:

```bash
docker compose -f docker-compose.mysql.yml up -d
```

See [LOCAL_DATABASE.md](LOCAL_DATABASE.md).

## Updating data assets

CSV files in `data/assets/` are mounted into the backend container. For admin UI edits that write back to CSV (contributions, allocations), use a **writable** mount or copy updated files from the container after edits.

```yaml
# Example: writable assets (if UI write-back needed)
- ./data/assets:/data/assets
```

After editing CSVs on the host, refresh the relevant portal page — read sync runs on load without rebuilding images.
