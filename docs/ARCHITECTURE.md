# Architecture — Automation Portal

## Vision

A single departmental system for CO-PO attainment, publications, projects, analytics, and AI-assisted insights. CO-PO is **one module** among several.

## Principles

1. **Preserve business logic** — `backend/app/copo/engine/legacy_engine.py` wraps the original CO-PO engine unchanged.
2. **Excel as I/O** — MySQL holds users, metadata, and JSON snapshots; marks files can be removed after processing.
3. **Backend aggregates analytics** — frontend does not compute heavy summaries from raw rows.
4. **Modular monorepo** — `backend/app/{auth,copo,publications,projects,ece_eve_projects,llm,analytics,awards,...}`.

## Layer diagram

```
React (frontend/src/modules/*)
        │  JWT
        ▼
FastAPI routers
        │
        ▼
Services (domain logic per module)
        │
        ▼
MySQL + filesystem storage
```

## CO-PO data lifecycle

| Stage | Storage |
|-------|---------|
| Upload | `copo_marks_uploads.storage_path` on disk |
| Process | Engine writes `*_CO_Percentage_Results.xlsx` |
| Persist | `copo_evaluation_runs.result_summary` (JSON) + `assessment_co_mapping` |
| Export | Short-lived download token |
| Archive | `copo_result_archives` + file under `storage/archives/` |

## Auth & RBAC

- JWT bearer tokens
- Roles: `faculty`, `hod`, `admin`
- Forgot password via SMTP; admin user lifecycle documented in [USER_MANAGEMENT.md](USER_MANAGEMENT.md)

## Module map

| Module | Backend path | Status |
|--------|--------------|--------|
| CO-PO | `backend/app/copo/` | Production |
| Publications | `backend/app/publications/` | Production |
| BTP/IP Projects | `backend/app/projects/` | Production |
| ECE/EVE Projects | `backend/app/ece_eve_projects/` | Production |
| Analytics | `backend/app/analytics/` | Production |
| LLM Insights | `backend/app/llm/` | Production (requires `GROQ_API_KEY`) |
| Awards | `backend/app/awards/` | Production |
| Auth | `backend/app/auth/` | Production |

Details: [MODULES.md](MODULES.md).

## Frontend structure

```
frontend/src/
  modules/auth/
  modules/copo/
  modules/publications/
  modules/projects/
  modules/analytics/
  modules/llm/
  modules/awards/
  layouts/          App shell & navigation
  pages/            Login, dashboard, admin
```

## Deployment

- **Development:** Uvicorn port **8001**, Vite port **5173**
- **Production:** [DEPLOYMENT.md](DEPLOYMENT.md) — Gunicorn, PM2, Nginx

## Legacy code

`legacy/flask-portal/` is archived for audit reference only. Do not deploy.
