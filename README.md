# Automation Portal (NPortal)

Unified departmental automation platform for the ECE Department at IIIT-D. Modules include **CO-PO attainment**, **Publications**, **BTP/IP Projects**, **ECE/EVE projects**, **Analytics**, **LLM insights**, and **Awards**.

## Stack

| Layer | Technology |
|-------|------------|
| API | FastAPI, SQLAlchemy, Alembic, JWT, bcrypt |
| Database | MySQL 8 (source of truth) |
| Frontend | React 19, Vite, Tailwind CSS |
| CO-PO engine | Preserved `legacy_engine.py` |
| Production | Gunicorn + Uvicorn workers, PM2 |

## Project layout

```
backend/              FastAPI application
frontend/             React SPA (Vite)
data/assets/          CO-PO mapping, faculty CSVs, Links.txt
data/sql/             MySQL bootstrap script
data/templates/       BTP/IP import template
backend/documents/    Meeting PDFs (folders in git; PDFs local only)
docs/                 Architecture & deployment guides
deploy/               Gunicorn + PM2 configs
legacy/               Archived Flask portal (reference only)
```

## Quick start (development)

### 1. MySQL

1. Install **MySQL Server 8.0** (port **3306**).
2. Copy `backend/.env.example` → `backend/.env` and set `MYSQL_*`.
3. Run `data/sql/local_mysql_bootstrap.sql` as root (optional).
4. `cd backend` → `alembic upgrade head`

Details: [docs/LOCAL_DATABASE.md](docs/LOCAL_DATABASE.md).

### 2. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Bootstrap admin: `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD` in `.env`.

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — API proxied to **http://127.0.0.1:8001**.

## Modules

| Module | Route (UI) | API prefix |
|--------|------------|------------|
| CO-PO | `/copo/*` | `/api/v1/copo` |
| Publications | `/publications` | `/api/v1/publications` |
| BTP/IP Projects | `/projects` | `/api/v1/projects` |
| ECE/EVE Projects | `/projects` (tab) | `/api/v1/ece-eve-projects` |
| Analytics | `/analytics` | `/api/v1/analytics` |
| LLM Insights | `/llm` | `/api/v1/llm-insights` |
| Awards | `/awards` | `/api/v1/awards` |
| Admin users | `/admin/users` | `/api/v1/auth` |

Full module reference: [docs/MODULES.md](docs/MODULES.md).

## Production deployment (IT)

See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for server requirements, environment variables, Nginx, PM2, backups, and upgrade steps.

```bash
cd backend && pip install -r requirements.txt && alembic upgrade head
cd ../frontend && npm ci && npm run build
pm2 start deploy/ecosystem.config.cjs
```

## Documentation

| Document | Purpose |
|----------|---------|
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Server hosting for IT |
| [docs/MODULES.md](docs/MODULES.md) | Feature reference |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design |
| [docs/LOCAL_DATABASE.md](docs/LOCAL_DATABASE.md) | MySQL setup |
| [docs/MAINTENANCE.md](docs/MAINTENANCE.md) | Ongoing operations (publications, CSV, meeting PDFs) |

## License

Internal departmental use — contact the ECE Department for distribution terms.
