# ECE Department Smart Portal (NPortal)

Unified departmental platform for the ECE Department at IIIT-D.

**Modules:** CO-PO attainment · Publications · Projects and Theses & ECE/EVE projects · Course allocation · Faculty contributions · Meeting minutes · Budget · Notifications & requirement tracker · Analytics · LLM insights · Faculty awards

## Stack

| Layer | Technology |
|-------|------------|
| API | FastAPI, SQLAlchemy, Alembic, JWT, bcrypt |
| Database | MySQL 8 (source of truth) |
| Frontend | React 19, Vite, Tailwind CSS |
| CO-PO engine | Preserved `legacy_engine.py` |
| Production | Gunicorn + Uvicorn workers, PM2 — or **Docker** (see below) |

## Project layout

```
backend/              FastAPI application
frontend/             React SPA (Vite)
data/assets/          Runtime CSV/Excel (gitignored — see docs/DATA_ASSETS.md)
data/sql/             MySQL bootstrap script
data/templates/       Projects and Theses import template
backend/documents/    Meeting PDFs (folders in git; PDFs local only)
docs/                 Architecture & deployment guides
deploy/               Gunicorn + PM2 configs
docker-compose.yml    Full-stack Docker (MySQL + API + frontend)
legacy/               Archived Flask portal (reference only)
```

## Quick start (development)

### 1. MySQL

1. Install **MySQL Server 8.0** (port **3306**).
2. Copy `backend/.env.example` → `backend/.env` and set `MYSQL_*`.
3. Run `data/sql/local_mysql_bootstrap.sql` as root (optional).
4. `cd backend` → `python -m alembic upgrade head`

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

Bootstrap admin (created on first API start if no admin exists):

```env
BOOTSTRAP_ADMIN_EMAIL=admin@ece.iiitd.ac.in
BOOTSTRAP_ADMIN_PASSWORD=ChangeMeOnFirstLogin!
```

Log in with those values, then **change the password immediately**. The eye icon on the password field toggles visibility. If login fails, the admin may already exist with a different password (bootstrap only runs once) — reset with `backend/scripts/reset_admin_password.py` or set `BOOTSTRAP_ADMIN_PASSWORD` and re-run that script.

On startup you should see `Requirement reminder scheduler active` if reminders are enabled (default).

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — API proxied to **http://127.0.0.1:8001**.

## AI (LLM insights + meeting-minutes Q&A)

Every LLM-backed feature (CO-PO insight narratives and the meeting-minutes RAG
chat) runs on a single **local, offline** model — free, no API key, no cloud
provider. Backed by [Ollama](https://ollama.com).

### Set up the local model (Ollama)

**Host install (testing servers):**

```bash
# 1. Install Ollama from https://ollama.com (runs a background service on :11434)
# 2. Pull a small, CPU-friendly model (recommended default ~2 GB):
ollama pull llama3.2:3b
# 3. Verify:
curl http://localhost:11434/v1/chat/completions \
  -d '{"model":"llama3.2:3b","messages":[{"role":"user","content":"Hello"}]}'
```

Config: `LOCAL_LLM_MODEL` (default `llama3.2:3b`),
`LOCAL_LLM_BASE_URL=http://host.docker.internal:11434/v1` inside Docker.

**Separate Docker stack (institute server without host Ollama):**

```bash
./scripts/generate_mtls_certs.sh   # or .\scripts\generate_mtls_certs.ps1
docker compose -f docker-compose.ollama.yml up -d
docker compose -f docker-compose.ollama.yml exec ollama ollama pull llama3.2:3b
# Then set LOCAL_LLM_BASE_URL=https://ollama-proxy:8443/v1 and LOCAL_LLM_MTLS_ENABLED=true
```

See [docs/SETUP.md](docs/SETUP.md) for the full dual-compose + mTLS flow.

Each LLM action shows a status dot for whether the local model is reachable.
`GET /api/v1/llm-insights/providers` reports availability.

## Modules (summary)

| Module | Route (UI) | API prefix |
|--------|------------|------------|
| CO-PO | `/copo/*` | `/api/v1/copo` |
| Publications | `/publications/*` | `/api/v1/publications` |
| Projects and Theses | `/projects` | `/api/v1/projects` |
| ECE/EVE Projects | `/projects` (tab) | `/api/v1/ece-eve-projects` |
| Course allocation | `/course-allocation` | `/api/v1/course-allocation` |
| Faculty contributions | `/contributions` | `/api/v1/contributions` |
| Faculty awards | `/awards` | `/api/v1/awards` |
| Meeting minutes | `/senate-minutes`, `/ece-faculty-meets`, … | `/api/v1/documents` |
| Budget | `/budget/accumulated-income`, `/budget/expenditure-budget`, `/budget/inventory` | `/api/v1/budget` |
| Notifications | `/notifications` (faculty), `/admin/notifications` | `/api/v1/notifications` |
| Requirement tracker | `/admin/requirement-tracker` | `/api/v1/notifications/admin/requirements` |
| Analytics | `/analytics` | `/api/v1/analytics` |
| LLM Insights | `/llm-insights` | `/api/v1/llm-insights` |
| Admin users | `/admin/users` | `/api/v1/auth` |

Full reference: [docs/MODULES.md](docs/MODULES.md).

## Production deployment

Prefer Docker on the institute server. Full walkthrough: [docs/SETUP.md](docs/SETUP.md).

| Method | Guide |
|--------|--------|
| **Full setup (start here)** | [docs/SETUP.md](docs/SETUP.md) |
| Native (PM2 + Nginx) | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |
| Docker (recommended for institute) | [docs/DOCKER_DEPLOYMENT.md](docs/DOCKER_DEPLOYMENT.md) |
| Backup / restore (restic) | [docs/BACKUP_RESTORE.md](docs/BACKUP_RESTORE.md) |
| Security review | [docs/SECURITY.md](docs/SECURITY.md) |
| Env variable reference | [docs/CONFIGURATION.md](docs/CONFIGURATION.md) |

### Env files you must edit (never commit)

| File | Copy from | What to change |
|------|-----------|----------------|
| `.env.docker` (app stack) | `.env.docker.example` | Secrets + URLs + SerpAPI — see below |
| `ops/backup/bac.env` | `ops/backup/bac.env.example` | `RESTIC_PASSWORD`, `BACKUP_TARGET_PATH`, schedule |
| `ops/backup/db.env` | `ops/backup/db.env.example` | MySQL passwords — **must match** `.env.docker` |

**`.env.docker` — change these before first production start:**

| Variable | Notes |
|----------|--------|
| `MYSQL_ROOT_PASSWORD`, `MYSQL_PASSWORD` | Strong unique passwords |
| `SECRET_KEY` | `openssl rand -hex 32` |
| `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD` | Defaults: `admin@ece.iiitd.ac.in` / `ChangeMeOnFirstLogin!` |
| `PORTAL_FRONTEND_URL`, `CORS_ORIGINS` | Real public URL (HTTPS on institute) |
| `SERP_API_KEYS` | Comma-separated SerpAPI keys for Scholar scraping (preferred). See [docs/CONFIGURATION.md](docs/CONFIGURATION.md#serpapi-keys) |
| `SCRAPER_BACKEND` | Keep `serpapi` in Docker (no browser for `scholarly`) |

**Backup envs:** set `RESTIC_PASSWORD` in `bac.env` (store offline — loss = unrecoverable backups). In `db.env`, set `MYSQL_PASSWORD` / `MYSQL_ROOT_PASSWORD` to the **same values** as `.env.docker`.

### SerpAPI keys (publications scrape)

1. Create free accounts at [https://serpapi.com/](https://serpapi.com/) (250 searches/month each, monthly reset).
2. Prefer **3–4 keys** so scraping can rotate when one hits quota.
3. Put them in **`SERP_API_KEYS`** (comma-separated) in `.env.docker` or `backend/.env`.  
   Example: `SERP_API_KEYS=key1,key2,key3`  
   Single-key fallback: `SERP_API_KEY=one_key` (used only if `SERP_API_KEYS` is empty).

```bash
# Docker — app stack
cp .env.docker.example .env.docker   # edit secrets (table above)
docker compose --env-file .env.docker up -d --build

# Docker — optional Ollama stack (shared network + mTLS)
./scripts/generate_mtls_certs.sh
docker compose -f docker-compose.ollama.yml up -d

# Docker — encrypted backups
cd ops/backup && cp bac.env.example bac.env && cp db.env.example db.env
# edit bac.env + db.env (table above), then:
docker compose -f docker-compose.backup.yml --env-file bac.env up -d --build
```

## Documentation

| Document | Purpose |
|----------|---------|
| [docs/SETUP.md](docs/SETUP.md) | **Start-to-finish setup (Windows + Linux)** |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | Handoff entry point |
| [docs/MODULES.md](docs/MODULES.md) | Feature reference |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | How to change code safely |
| [docs/FILE_INVENTORY.md](docs/FILE_INVENTORY.md) | Per-file purpose list |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Server hosting (native) |
| [docs/DOCKER_DEPLOYMENT.md](docs/DOCKER_DEPLOYMENT.md) | Docker hosting |
| [docs/BACKUP_RESTORE.md](docs/BACKUP_RESTORE.md) | Restic encrypted backup / restore |
| [docs/SECURITY.md](docs/SECURITY.md) | OWASP checklist + blackbox probes |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design |
| [docs/LOCAL_DATABASE.md](docs/LOCAL_DATABASE.md) | MySQL setup |
| [docs/DATA_ASSETS.md](docs/DATA_ASSETS.md) | `data/assets/` setup (not in Git) |

## License

Internal departmental use — contact the ECE Department for distribution terms.
