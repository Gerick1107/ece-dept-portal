# Development guide

## Local loop

1. MySQL 8 on `3306` with credentials from `backend/.env`
2. `cd backend` → activate venv → `alembic upgrade head` → `uvicorn app.main:app --reload --port 8001`
3. `cd frontend` → `npm run dev` → http://localhost:5173 (proxies `/api` to 8001)

Interactive OpenAPI (dev only): http://127.0.0.1:8001/api/docs

## Adding a backend endpoint

1. Prefer putting routes under the owning module router (e.g. `backend/app/publications/routes/router.py`).
2. Put business logic in `services/`, models in `models/`, request/response shapes in `schemas/`.
3. Register new top-level routers in `backend/app/main.py` (`api.include_router(...)`).
4. Import new SQLAlchemy models from `backend/app/database/models/__init__.py` so metadata / Alembic see them.
5. Protect with `get_current_user`, `require_roles(...)`, and/or `FacultyScopeDep`.

## Adding a frontend page

1. Create a page under `frontend/src/modules/<domain>/pages/`.
2. Register the route in `frontend/src/App.tsx`.
3. Add nav links in `frontend/src/layouts/AppLayout.tsx` (and module hub cards if used).
4. Call the API through `frontend/src/services/api.ts` helpers (`apiGet`, `apiPostJson`, …).

## Adding a database change

1. Edit SQLAlchemy models.
2. Create a migration under `backend/alembic/versions/` (copy the style of recent revisions; set `down_revision` to current head).
3. Run `alembic upgrade head` locally and on the server after deploy.
4. Document the migration in [DATABASE.md](DATABASE.md).

Current head (as of this handoff wave): `038_sdg_ever_accepted` (after `037_student_publications`).

## Publications-specific notes

| Concern | Where |
|---------|-------|
| Scholar sync | `backend/app/publications/services/gap_fill_service.py` |
| Blocked deletes | `blocked_publications` + `delete_publications()` |
| Manual edit protection | `publications.manual_overrides` JSON list |
| Books tab (manual) | `publications.is_manual_book` |
| Book chapters tab | non-empty `publications.book` from Scholar |
| Repository link ban | `utils/link_filters.py` (`repository.iiitd.edu.in`) |
| Student publications | `student_publications` table + `/publications/student-publications` |
| Faculty Admin CSV | `services/faculty_master_csv.py` writes `data/assets/faculty_master.csv` |

## Code style

- Prefer explicit service functions over fat route handlers.
- Keep UI wording consistent with nav labels (e.g. **Projects and Theses**).
- Avoid introducing new cloud LLM providers; local Ollama is the supported path.
