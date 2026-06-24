# Docker deployment (institute server)

When the portal is feature-complete, deploy the **entire stack** (MySQL + API + frontend) with Docker. This pins Python 3.11, Node 20, and MySQL 8.0 so host Python/Node upgrades cannot break the portal.

## Prerequisites

- Docker Engine 24+ and Docker Compose v2
- Git clone of this repository on the server
- `data/assets/` populated with CSV/Excel seed files

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

4. **CSV assets** — Keep `data/assets/` in sync via Git. Docker mounts this folder into the backend; edits on either machine should be committed.

5. **Local ports** — Default UI is `http://localhost:8080`. If both run Docker on one machine, only one stack can bind the port; use different `PORTAL_HTTP_PORT` in `.env.docker` per developer.

6. **Do not commit** — `.env.docker`, SQL dumps with real credentials, or `storage/` uploads unless your team explicitly wants them in a private repo.

## Quick start

```bash
cd /opt/automation-portal   # or your clone path
cp .env.docker.example .env.docker
# Edit .env.docker — set SECRET_KEY, passwords, PORTAL_FRONTEND_URL, CORS_ORIGINS

docker compose --env-file .env.docker up -d --build
```

Open `http://<server>:8080` (or the port set in `PORTAL_HTTP_PORT`).

Default bootstrap admin comes from `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD` in `.env.docker` (created on first API startup if no admin exists). **Change the password immediately after first login.**

## Services

| Service | Role |
|---------|------|
| `mysql` | MySQL 8.0 database (persistent volume `mysql_data`) |
| `backend` | FastAPI on port 8000 (internal); runs `alembic upgrade head` on start |
| `frontend` | Nginx serving the React build; proxies `/api/` to backend |

## Environment variables (backend / `.env.docker`)

| Variable | Default | Purpose |
|----------|---------|---------|
| `ENABLE_REQUIREMENT_REMINDERS` | `true` | Requirement reminder background job |
| `REQUIREMENT_REMINDER_POLL_MINUTES` | `1` | How often due reminders are checked |
| `ENABLE_SCHEDULER` | `false` | Monthly publication gap-fill only |
| `SMTP_ENABLED` | `false` | Required for email reminders in production |

## Production hardening checklist

Before IT security review:

1. Set strong `SECRET_KEY` (`openssl rand -hex 32`)
2. Set strong `MYSQL_ROOT_PASSWORD` and `MYSQL_PASSWORD`
3. Set `APP_ENV=production` and `DEBUG=false` (already in compose)
4. Set `PORTAL_FRONTEND_URL` and `CORS_ORIGINS` to the real HTTPS URL
5. Put **TLS** in front (institute reverse proxy / load balancer terminating HTTPS)
6. Restrict MySQL port — do **not** publish 3306 to the internet (compose does not expose it)
7. Enable SMTP for password reset emails if required
8. Review [SECURITY.md](SECURITY.md)

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
