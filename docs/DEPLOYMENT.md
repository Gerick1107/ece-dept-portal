# Deployment guide (IT / server hosting)

This document describes how to host **Automation Portal** (NPortal) on a departmental server. The stack is **FastAPI + MySQL + React (Vite)**.

For containerized deployment, see **[DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)** (recommended when Python/Node versions on the host must not affect the portal).

## 1. Server requirements

| Component | Minimum |
|-----------|---------|
| OS | Linux (Ubuntu 22.04+ recommended) or Windows Server |
| Python | 3.11+ |
| Node.js | 20 LTS (build frontend only) |
| MySQL | 8.0+ |
| Reverse proxy | Nginx or IIS (recommended) |
| Process manager | PM2 (`deploy/ecosystem.config.cjs`) or systemd |

## 2. Clone and layout

```bash
git clone <repository-url> /opt/automation-portal
cd /opt/automation-portal
```

| Path | Purpose |
|------|---------|
| `backend/` | API application |
| `frontend/` | React SPA source |
| `data/assets/` | Runtime CSV/Excel — **gitignored**; see [DATA_ASSETS.md](DATA_ASSETS.md) |
| `backend/storage/` | Runtime uploads & results |
| `backend/documents/` | Meeting PDFs (optional `DOCUMENTS_DIR`) |
| `deploy/` | Gunicorn + PM2 configs |
| `docker-compose.yml` | Alternative full-stack Docker deploy |

## 3. MySQL setup

```sql
CREATE DATABASE ece_dept_portal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'portal_user'@'localhost' IDENTIFIED BY '<strong-password>';
GRANT ALL PRIVILEGES ON ece_dept_portal.* TO 'portal_user'@'localhost';
FLUSH PRIVILEGES;
```

Apply schema:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
```

See [LOCAL_DATABASE.md](LOCAL_DATABASE.md) for Windows dev notes.

## 4. Environment configuration

Copy `backend/.env.example` → `backend/.env`. **Never commit `.env`.**

### Required

| Variable | Description |
|----------|-------------|
| `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` | Database |
| `SECRET_KEY` | Long random string for JWT |
| `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_PASSWORD` | First admin |
| `PORTAL_FRONTEND_URL` | Public SPA URL (email links) |
| `CORS_ORIGINS` | Comma-separated allowed origins |

### Email (password reset, notifications, reminders)

| Variable | Description |
|----------|-------------|
| `SMTP_ENABLED` | `true` in production |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL` | Mail server |

### Publications scraper

| Variable | Description |
|----------|-------------|
| `SERP_API_KEY` | SerpAPI key |
| `SCRAPER_BACKEND` | `scholarly` or `serpapi` |
| `ENABLE_SCHEDULER` | `true` for **monthly** publication gap-fill only |

### Requirement auto-reminders

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_REQUIREMENT_REMINDERS` | `true` | Email/portal reminders until tracker is green |
| `REQUIREMENT_REMINDER_POLL_MINUTES` | `1` | Background check interval (minutes) |

Independent of `ENABLE_SCHEDULER`.

### LLM insights

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Groq API key |

### CO-PO assets (auto-resolved if unset)

| Variable | Default |
|----------|---------|
| `DEFAULT_MAPPING_PATH` | `data/assets/default_mapping.xlsx` |

## 5. Build frontend

```bash
cd frontend
npm ci
npm run build
```

Output: `frontend/dist/`. Use relative `/api/v1` when Nginx proxies API on same host.

## 6. Run backend (production)

```bash
cd /opt/automation-portal/backend
pip install -r requirements.txt gunicorn
alembic upgrade head
cd ..
pm2 start deploy/ecosystem.config.cjs
pm2 save
```

### Nginx example

```nginx
server {
    listen 80;
    server_name portal.ece.example.edu;
    root /opt/automation-portal/frontend/dist;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

Health check: `GET /health`

## 7. Post-deploy checklist

- [ ] `alembic upgrade head` on every release
- [ ] `SECRET_KEY` and bootstrap password changed
- [ ] HTTPS enabled; `CORS_ORIGINS` matches production URL
- [ ] SMTP tested (welcome, forgot-password, notification)
- [ ] `ENABLE_REQUIREMENT_REMINDERS=true` and reminder log on startup
- [ ] `data/assets/` populated on server (not from Git — copy from team bundle or DB export)
- [ ] `backend/storage/` and `backend/documents/` writable
- [ ] MySQL not exposed to the internet
- [ ] Review [SECURITY.md](SECURITY.md)

## 8. Upgrades

```bash
git pull
cd backend && source .venv/bin/activate && pip install -r requirements.txt && alembic upgrade head
cd ../frontend && npm ci && npm run build
pm2 restart all
```

## 9. Backups

- **MySQL:** regular `mysqldump` of `ece_dept_portal`
- **Files:** `backend/storage/archives/`, `data/assets/` (backup separately), `backend/documents/` (PDFs)

## 10. Troubleshooting

| Symptom | Check |
|---------|-------|
| 502 / API down | `pm2 logs`, Gunicorn port, MySQL credentials |
| CORS errors | `CORS_ORIGINS` |
| No reminder emails | `ENABLE_REQUIREMENT_REMINDERS`, SMTP, backend logs for scheduler line |
| Monthly sync not running | `ENABLE_SCHEDULER=true` (separate from reminders) |
| Contributions revert after delete | CSV write-back; check `data/assets/` permissions |

Further detail: [MODULES.md](MODULES.md), [MAINTENANCE.md](MAINTENANCE.md).
