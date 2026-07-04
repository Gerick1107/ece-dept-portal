# Automation Portal (NPortal)

Unified departmental automation platform for the ECE Department at IIIT-D.

**Modules:** CO-PO attainment · Publications · BTP/IP & ECE/EVE projects · Course allocation · Faculty contributions · Meeting minutes · Budget · Notifications & requirement tracker · Analytics · LLM insights · Faculty awards

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
data/templates/       BTP/IP import template
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

Bootstrap admin: `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD` in `.env`.

On startup you should see `Requirement reminder scheduler active` if reminders are enabled (default).

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — API proxied to **http://127.0.0.1:8001**.

## AI providers (LLM insights + meeting-minutes Q&A)

Every LLM-backed feature (CO-PO insight narratives and the meeting-minutes RAG
chat) can run against **either** of two providers, chosen per request from a
toggle in the UI:

- **Cloud (Groq)** — fast, online. Set `GROQ_API_KEY`. The model is config-driven
  via `GROQ_MODEL` (default `openai/gpt-oss-120b`), so a Groq model deprecation
  only needs an env change, no code change.
- **Local (Offline)** — free, fully local, no API key. Backed by
  [Ollama](https://ollama.com).

### Set up the local provider (Ollama)

```bash
# 1. Install Ollama from https://ollama.com (runs a background service on :11434)
# 2. Pull a small, CPU-friendly model (recommended default ~2 GB):
ollama pull llama3.2:3b
# Alternatives to benchmark:
#   ollama pull phi3:mini
#   ollama pull mistral:7b-instruct-q4_K_M   # heavier; MUST be the Q4 quant for CPU speed
# 3. Verify it answers in seconds, not minutes:
curl http://localhost:11434/v1/chat/completions \
  -d '{"model":"llama3.2:3b","messages":[{"role":"user","content":"Hello"}]}'
```

Config (`backend/.env` or `.env.docker`): `LOCAL_LLM_MODEL` (default
`llama3.2:3b`), `LOCAL_LLM_BASE_URL` (default `http://localhost:11434/v1`),
`DEFAULT_LLM_PROVIDER` (`groq` or `local`).

> Docker note: Ollama runs on the **host**, so the backend container reaches it
> via `http://host.docker.internal:11434/v1` (already wired in `docker-compose.yml`).

### Switching providers

- **UI:** each LLM action (Generate Insights, Ask about minutes) shows a
  **Cloud (Groq) / Local (Offline)** toggle; the choice persists per session and
  a dot shows whether the provider is currently reachable.
- **API:** send `"provider": "groq"` or `"provider": "local"` in the request body
  to `POST /api/v1/llm-insights/generate` and `POST /api/v1/documents/{type}/query`.
  `GET /api/v1/llm-insights/providers` reports availability of each.

A 3B–7B local model is weaker than the cloud model on hard reasoning — expected
tradeoff for zero-cost / offline, not a bug.

## Modules (summary)

| Module | Route (UI) | API prefix |
|--------|------------|------------|
| CO-PO | `/copo/*` | `/api/v1/copo` |
| Publications | `/publications/*` | `/api/v1/publications` |
| BTP/IP Projects | `/projects` | `/api/v1/projects` |
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

| Method | Guide |
|--------|--------|
| Native (PM2 + Nginx) | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |
| Docker (recommended for institute) | [docs/DOCKER_DEPLOYMENT.md](docs/DOCKER_DEPLOYMENT.md) |
| Security review | [docs/SECURITY.md](docs/SECURITY.md) |

```bash
# Native
cd backend && pip install -r requirements.txt && alembic upgrade head
cd ../frontend && npm ci && npm run build
pm2 start deploy/ecosystem.config.cjs

# Docker
cp .env.docker.example .env.docker   # edit secrets
docker compose --env-file .env.docker up -d --build
```

## Documentation

| Document | Purpose |
|----------|---------|
| [docs/MODULES.md](docs/MODULES.md) | Feature reference |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Server hosting (native) |
| [docs/DOCKER_DEPLOYMENT.md](docs/DOCKER_DEPLOYMENT.md) | Docker hosting |
| [docs/SECURITY.md](docs/SECURITY.md) | OWASP checklist |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design |
| [docs/LOCAL_DATABASE.md](docs/LOCAL_DATABASE.md) | MySQL setup |
| [docs/DATA_ASSETS.md](docs/DATA_ASSETS.md) | `data/assets/` setup (not in Git) |

## License

Internal departmental use — contact the ECE Department for distribution terms.
