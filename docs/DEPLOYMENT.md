# Deployment guide (IT / server hosting)

This document describes how to host **Automation Portal** (NPortal) on a departmental server. The stack is **FastAPI + MySQL + React (Vite)**.

## 1. Server requirements

| Component | Minimum |
|-----------|---------|
| OS | Linux (Ubuntu 22.04+ recommended) or Windows Server |
| Python | 3.11+ |
| Node.js | 20 LTS (build frontend only) |
| MySQL | 8.0+ |
| Reverse proxy | Nginx or IIS (optional but recommended) |
| Process manager | PM2 (`deploy/ecosystem.config.cjs`) or systemd |

## 2. Clone and layout

```bash
git clone <repository-url> /opt/automation-portal
cd /opt/automation-portal
```

Important directories:

| Path | Purpose |
|------|---------|
| `backend/` | API application |
| `frontend/` | React SPA source |
| `data/assets/` | CO-PO mapping files, faculty CSV, `Links.txt` |
| `backend/storage/` | Runtime uploads & results (created automatically) |
| `deploy/` | Gunicorn + PM2 configs |

## 3. MySQL setup

1. Create database and user (example):

```sql
CREATE DATABASE ece_dept_portal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'portal_user'@'localhost' IDENTIFIED BY '<strong-password>';
GRANT ALL PRIVILEGES ON ece_dept_portal.* TO 'portal_user'@'localhost';
FLUSH PRIVILEGES;
```

2. Optional bootstrap script: `data/sql/local_mysql_bootstrap.sql`

3. Apply schema:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
```

4. Verify: `python scripts/verify_db.py`

See [LOCAL_DATABASE.md](LOCAL_DATABASE.md) for Windows-specific notes.

## 4. Environment configuration

Copy `backend/.env.example` → `backend/.env`. **Never commit `.env`.**

### Required

| Variable | Description |
|----------|-------------|
| `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` | Database connection |
| `SECRET_KEY` | Long random string for JWT signing |
| `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_PASSWORD` | First admin (created on first startup if no users) |
| `PORTAL_FRONTEND_URL` | Public URL of the SPA (for email links) |
| `CORS_ORIGINS` | Comma-separated allowed origins (production frontend URL) |

### Email (password reset / welcome)

| Variable | Description |
|----------|-------------|
| `SMTP_ENABLED` | `true` in production |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` | Mail server |
| `SMTP_FROM_EMAIL` | Sender address |

### Publications scraper

| Variable | Description |
|----------|-------------|
| `SERP_API_KEY` | SerpAPI key (recommended when Google Scholar blocks) |
| `SCRAPER_BACKEND` | `scholarly` or `serpapi` |
| `ENABLE_SCHEDULER` | `true` to run periodic publication sync |

### LLM insights

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Groq API key for AI insights module |

### CO-PO assets (auto-resolved if unset)

| Variable | Default |
|----------|---------|
| `DEFAULT_MAPPING_PATH` | `data/assets/default_mapping.xlsx` |
| PG mapping | `data/assets/CO mapping - PG.xlsx` |

## 5. Build frontend

```bash
cd frontend
npm ci
npm run build
```

Production static files are in `frontend/dist/`.

Set `VITE_API_BASE` only if the API is on a different host than the SPA. For same-origin Nginx proxy, leave default (relative `/api/v1`).

## 6. Run backend (production)

### Linux + Gunicorn + PM2

Edit `deploy/ecosystem.config.cjs` paths for Linux:

- `backend/.venv/bin/python` instead of Windows `Scripts/python.exe`
- Use `gunicorn` from venv

```bash
cd /opt/automation-portal/backend
pip install -r requirements.txt gunicorn
alembic upgrade head
cd ..
pm2 start deploy/ecosystem.config.cjs
pm2 save
```

`deploy/gunicorn.conf.py` binds the API (default port **8001**).

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

Health check: `GET /health` (outside `/api/v1`).

## 7. Post-deploy checklist

- [ ] `alembic upgrade head` on every release
- [ ] `backend/.env` secured (chmod 600)
- [ ] `SECRET_KEY` and `BOOTSTRAP_ADMIN_PASSWORD` changed from defaults
- [ ] Admin logs in and changes password
- [ ] SMTP tested via forgot-password flow
- [ ] `data/assets/faculty_master.csv` present for publications
- [ ] `data/assets/Links.txt` present for lab/center affiliations
- [ ] `backend/storage/` writable by API process
- [ ] Firewall allows HTTP/HTTPS only (not direct MySQL from internet)

## 8. Upgrades

```bash
git pull
cd backend && source .venv/bin/activate && pip install -r requirements.txt && alembic upgrade head
cd ../frontend && npm ci && npm run build
pm2 restart all
```

## 9. Backups

- **MySQL:** regular `mysqldump` of `ece_dept_portal`
- **Files:** `backend/storage/archives/` (CO-PO result archives), `data/assets/` (mapping & faculty data)

## 10. Troubleshooting

| Symptom | Check |
|---------|-------|
| 502 / API down | `pm2 logs`, Gunicorn bind port, `.env` MySQL credentials |
| Login works, data empty | Migrations applied? `alembic current` |
| CORS errors | `CORS_ORIGINS` includes frontend URL |
| LLM insights unavailable | `GROQ_API_KEY` set; regenerate after prompt updates |
| Affiliations stale | Edit `data/assets/Links.txt`; sync runs on API startup and faculty affiliations page load |

Further module detail: [MODULES.md](MODULES.md). Operations: [MAINTENANCE.md](MAINTENANCE.md).
