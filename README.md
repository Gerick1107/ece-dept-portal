# ECE Department Automation Portal (NPortal)

Unified departmental automation platform for the ECE Department at IIIT-D. The legacy **CO-PO Attainment Portal** runs as the `copo` module; **Publications** and **BTP/IP Projects** modules are integrated in the current release.

## Stack

| Layer | Technology |
|-------|------------|
| API | FastAPI, SQLAlchemy, Alembic, JWT, bcrypt |
| Database | MySQL 8 (source of truth) |
| Frontend | React 19, Vite, Tailwind CSS |
| CO-PO engine | Preserved `legacy_engine.py` (from `ece_orignal_updated.py`) |
| Production | Gunicorn + Uvicorn workers, PM2 |

## Project layout

```
backend/              FastAPI application
frontend/             React SPA (Vite)
data/assets/          Default CO-PO mapping & indirect Excel
data/sql/             Local MySQL bootstrap script
data/templates/       BTP/IP import template
docs/                 Architecture & operations guides
deploy/               Gunicorn + PM2 configs
legacy/               Archived Flask portal (reference only)
```

## Quick start (development)

### 1. MySQL (Windows — no Docker)

Use **MySQL Server 8.0** on **port 3306**.

1. Start service **MySQL80** (Windows Services).
2. Copy `backend/.env.example` → `backend/.env` and set `MYSQL_*` credentials.
3. Run `data/sql/local_mysql_bootstrap.sql` in Workbench as **root** (optional if using root in `.env`).
4. Import schema: `cd backend` → `alembic upgrade head`
5. Verify: `python scripts/verify_db.py`

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

Bootstrap admin (first run): `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD` in `.env`.

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — API is proxied to **http://127.0.0.1:8001** (`frontend/vite.config.ts`).

**Important:** Start the backend before using the frontend. `ECONNREFUSED 127.0.0.1:8001` means the API is not running.

## Modules

| Module | Route (UI) | API prefix |
|--------|------------|------------|
| CO-PO | `/copo/*` | `/api/v1/copo` |
| Publications | `/publications` | `/api/v1/publications` |
| BTP/IP Projects | `/projects` | `/api/v1/projects` |
| Admin users | `/admin/users` | `/api/v1/auth` |

## Auth features

- JWT login (`POST /api/v1/auth/login/json`)
- Forgot password → temporary password email (`POST /api/v1/auth/forgot-password`, requires SMTP)
- Admin user management: create, deactivate, activate, remove profile (see [docs/USER_MANAGEMENT.md](docs/USER_MANAGEMENT.md))

## CO-PO API (parity with legacy Flask)

| Legacy | New |
|--------|-----|
| `GET/POST /api/course_names` | `GET/POST /api/v1/copo/course-names` |
| `POST /api/parse_students` | `POST /api/v1/copo/parse-students` |
| `POST /` (evaluate) | `POST /api/v1/copo/evaluate` |
| `GET /download_results/<id>` | `GET /api/v1/copo/download/{token}` |

Full mapping: [docs/WORKFLOW_A.md](docs/WORKFLOW_A.md).

## Environment variables

Copy `backend/.env.example` → `backend/.env`. Never commit `.env` (see `.gitignore`).

Key settings:

- `MYSQL_*` — database connection
- `SECRET_KEY` — JWT signing (change in production)
- `SMTP_*` — welcome / password-reset emails
- `ENABLE_SDG_LLM=false` — manual SDG editing only (recommended until LLM module)

## Production (VM)

```bash
cd backend && pip install -r requirements.txt
alembic upgrade head
cd .. && pm2 start deploy/ecosystem.config.cjs
```

Adjust `deploy/ecosystem.config.cjs` for Linux paths.

## Documentation index

| Document | Purpose |
|----------|---------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design |
| [docs/LOCAL_DATABASE.md](docs/LOCAL_DATABASE.md) | MySQL setup |
| [docs/STORAGE.md](docs/STORAGE.md) | File storage layout |
| [docs/USER_MANAGEMENT.md](docs/USER_MANAGEMENT.md) | Accounts & password reset |
| [docs/TASK_2B_TESTING.md](docs/TASK_2B_TESTING.md) | Publications & projects testing |
| [docs/MAINTENANCE.md](docs/MAINTENANCE.md) | Ongoing operations |

## GitHub

Before pushing:

1. Ensure `backend/.env` is not tracked (listed in `.gitignore`).
2. Run `alembic upgrade head` on any deployment target.
3. Do not commit `node_modules/`, `backend/storage/`, or database dumps.

## License

Internal departmental use — contact the ECE Department for distribution terms.
