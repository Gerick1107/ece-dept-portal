# Architecture — ECE Department Automation Portal

## Vision

A single departmental system where CO-PO attainment is **one module** among several. Current release includes **CO-PO**, **Publications**, and **BTP/IP Projects**.

## Principles

1. **Preserve business logic** — `backend/app/copo/engine/legacy_engine.py` is a direct lift of `ece_orignal_updated.py`; services wrap it unchanged.
2. **Excel as I/O only** — MySQL holds users, upload sessions, evaluation metadata, and archives; marks files are removable after processing.
3. **Backend aggregates analytics** — frontend must not compute heavy summaries from raw rows.
4. **Modular monorepo** — `backend/app/{auth,copo,publications,projects,...}`.

## Layer diagram

```
React (frontend/src/modules/*)
        │  JWT
        ▼
FastAPI routers (auth, copo, publications, projects, …)
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
| Persist | `copo_evaluation_runs.result_summary` (JSON) |
| Export | Short-lived download token |
| Archive | `copo_result_archives` + file under `storage/archives/` |
| Cleanup | Marks file deleted; upload row status `cleared` |

User accounts are never hard-deleted when CO-PO data exists; see [USER_MANAGEMENT.md](USER_MANAGEMENT.md).

## Auth & RBAC

- JWT bearer tokens (`Authorization` header)
- Roles: `faculty`, `hod`, `admin`
- Passwords: bcrypt
- Forgot password: temporary password email (SMTP)
- Admin: deactivate / activate / remove profile (anonymize, keep `user_id` for CO-PO FKs)

## Module status

| Module | Path | Status |
|--------|------|--------|
| CO-PO | `backend/app/copo/` | Production |
| Publications | `backend/app/publications/` | Production (SerpAPI / scholarly) |
| BTP/IP Projects | `backend/app/projects/` | Production (manual SDG; LLM optional via `ENABLE_SDG_LLM`) |
| Auth | `backend/app/auth/` | Production |
| Analytics / Reports / Reminders / LLM | scaffolded | Future |

## Frontend structure

```
frontend/src/
  modules/auth/       AuthContext, protected routes
  modules/copo/       CO-PO workflows
  modules/publications/
  modules/projects/   BTP/IP repository
  pages/              Admin, login, profile, dashboard
```

## Deployment

- **Development:** `uvicorn` on port **8001**, Vite on **5173**
- **Production:** Gunicorn + Uvicorn workers, PM2 (`deploy/ecosystem.config.cjs`)
- **Nginx (optional):** proxy `/api` → backend, serve `frontend/dist`

## Legacy code

Flask `legacy/flask-portal/` is archived for audit reference only. Do not deploy for the new portal.

## Related docs

- [LOCAL_DATABASE.md](LOCAL_DATABASE.md)
- [STORAGE.md](STORAGE.md)
- [USER_MANAGEMENT.md](USER_MANAGEMENT.md)
- [TASK_2B_TESTING.md](TASK_2B_TESTING.md)
