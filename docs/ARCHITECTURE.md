# Architecture — Automation Portal

## Vision

A single departmental system for CO-PO attainment, publications, projects, course allocation, faculty contributions, meeting minutes, notifications, analytics, and AI-assisted insights.

## Principles

1. **Preserve business logic** — `backend/app/copo/engine/legacy_engine.py` wraps the original CO-PO engine unchanged.
2. **Excel/CSV as operational I/O** — MySQL holds users, transactional data, and JSON snapshots; many modules sync from `data/assets/` CSVs.
3. **Backend aggregates analytics** — frontend does not compute heavy summaries from raw rows.
4. **Modular monorepo** — `backend/app/{auth,copo,publications,projects,course_allocation,contributions,documents,notifications,...}`.

## Layer diagram

```
React (frontend/src/modules/*)
        │  JWT
        ▼
FastAPI routers + security middleware
        │
        ▼
Services (domain logic per module)
        │
        ├── APScheduler (requirement reminders; optional publication sync)
        ▼
MySQL + filesystem storage
```

## CO-PO data lifecycle

| Stage | Storage |
|-------|---------|
| Upload | `copo_marks_uploads.storage_path` |
| Process | Engine → `*_CO_Percentage_Results.xlsx` |
| Persist | `copo_evaluation_runs.result_summary` + `assessment_co_mapping` |
| Archive | `copo_result_archives` + `storage/archives/` |

## Auth & RBAC

- JWT bearer tokens; roles: `faculty`, `hod`, `admin`
- Login rate limiting; security headers in production
- Forgot password via SMTP — [USER_MANAGEMENT.md](USER_MANAGEMENT.md)

## Module map

| Module | Backend path | Notes |
|--------|--------------|-------|
| CO-PO | `backend/app/copo/` | Legacy engine preserved |
| Publications | `backend/app/publications/` | Scholar/SerpAPI sync |
| BTP/IP Projects | `backend/app/projects/` | SDG tagging |
| ECE/EVE Projects | `backend/app/ece_eve_projects/` | Mirror of BTP subset |
| Course allocation | `backend/app/course_allocation/` | CSV + XLSX upload |
| Contributions | `backend/app/contributions/` | Multi-tab faculty data |
| Awards | `backend/app/awards/` | CSV sync |
| Documents / Minutes | `backend/app/documents/` | PDF storage + ingestion |
| Notifications | `backend/app/notifications/` | Tracker, replies, reminders |
| Analytics | `backend/app/analytics/` | Dashboards |
| LLM Insights | `backend/app/llm/` | Groq narratives |
| Auth | `backend/app/auth/` | Users, JWT |

Details: [MODULES.md](MODULES.md).

## Background jobs

| Job | Trigger | Env flag |
|-----|---------|----------|
| Requirement reminders | Interval (default 1 min) | `ENABLE_REQUIREMENT_REMINDERS` (default on) |
| Publication monthly gap-fill | Cron 1st @ 02:00 UTC | `ENABLE_SCHEDULER` (default off) |

Reminders send email when SMTP is enabled; portal notification fallback when SMTP is off. Stops when requirement tracker cell is green.

## Frontend structure

```
frontend/src/
  modules/auth, copo, publications, projects, analytics, llm, awards
  modules/contributions, course_allocation, documents, notifications
  layouts/          App shell & navigation
  pages/            Login, dashboard, admin
```

Role-based nav: e.g. Course Catalog admin-only; faculty see Notifications, not admin tracker.

## Deployment options

| Mode | Guide |
|------|--------|
| Native (PM2 + Nginx) | [DEPLOYMENT.md](DEPLOYMENT.md) |
| Docker | [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) |
| Security | [SECURITY.md](SECURITY.md) |

Dev: Uvicorn **8001**, Vite **5173**.

## Legacy code

`legacy/flask-portal/` is archived for audit reference only. Do not deploy.
