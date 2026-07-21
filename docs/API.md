# API overview

Interactive docs (development only): `http://127.0.0.1:8001/api/docs`

All routes are mounted under `API_V1_PREFIX` (default `/api/v1`).

## Auth

| Method | Path | Notes |
|--------|------|-------|
| POST | `/auth/login/json` | Returns JWT |
| GET | `/auth/me` | Current user (includes `faculty_id`) |
| CRUD-ish | `/auth/users*` | Admin user management |

## Publications (high-signal)

| Method | Path | Notes |
|--------|------|-------|
| GET | `/publications/faculty` | Directory (scoped) |
| POST | `/publications/faculty` | Admin Faculty Admin create |
| GET/PATCH/DELETE | `/publications/publications`… | List / edit / delete (faculty can manage own) |
| POST | `/publications/scrape/sync-all` | Admin Scholar gap-fill |
| GET/POST/DELETE | `/publications/student-publications`… | Shared student list |
| GET | `/publications/student-publications/template` | Excel template |
| GET | `/publications/exports` | CSV/XLSX/PDF/DOCX |

Query params on publication list: `query`, `search_by=title|venue`, `category=journals|conferences|book_chapters|books|preprints`, `is_patent`, `faculty_id`.

## Other prefixes

| Prefix | Module |
|--------|--------|
| `/copo` | CO-PO |
| `/projects` | Projects and Theses |
| `/ece-eve-projects` | ECE/EVE |
| `/course-allocation` | Allocations |
| `/documents` | Minutes + RAG |
| `/budget` | Budget |
| `/notifications` | Notifications / requirements |
| `/awards` | Awards |
| `/contributions` | Contributions |
| `/analytics` | Analytics |
| `/llm-insights` | Local LLM narratives |

For exhaustive schemas, use OpenAPI in development rather than duplicating every field here.
