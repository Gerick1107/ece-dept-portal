# Portal modules reference

Automation Portal (NPortal) is a modular departmental system. Each module has a UI route and API prefix under `/api/v1`.

## Auth & users

| Item | Detail |
|------|--------|
| UI | `/login`, `/profile`, `/admin/users` |
| API | `/api/v1/auth` |
| Roles | `faculty`, `hod`, `admin` |
| Features | JWT login, forgot password (SMTP), admin user CRUD, deactivate/remove profile |

Docs: [USER_MANAGEMENT.md](USER_MANAGEMENT.md)

## CO-PO attainment

| Item | Detail |
|------|--------|
| UI | `/copo/*` (evaluate, compare, bulk, archives, generator) |
| API | `/api/v1/copo` |
| Engine | `backend/app/copo/engine/legacy_engine.py` (preserved legacy logic) |
| Inputs | Consolidated marks Excel, UG/PG CO-PO mapping |
| Outputs | Result Excel, JSON snapshot in MySQL, download tokens |

Workflow: [WORKFLOW_A.md](WORKFLOW_A.md)

Key features:

- Programme / branch evaluation scope from marks file
- UG and PG mapping profiles
- Section labels and semester tagging
- Assessment-to-CO structure stored for analytics and LLM

## Courses

| Item | Detail |
|------|--------|
| API | `/api/v1/courses` |
| Purpose | Course catalogue used across CO-PO and insights |

## Analytics

| Item | Detail |
|------|--------|
| UI | `/analytics` |
| API | `/api/v1/analytics` |
| Data | Aggregated CO-PO snapshots, departmental KPIs |

## LLM insights

| Item | Detail |
|------|--------|
| UI | `/llm` |
| API | `/api/v1/llm-insights` |
| Provider | Groq (`GROQ_API_KEY`) |
| Purpose | Semester-over-semester CO/PO comparison narratives with assessment structure context |

Requires prior CO-PO evaluation runs. Cached per course/semester pair; use **Regenerate** after new evaluations.

## Publications

| Item | Detail |
|------|--------|
| UI | `/publications` |
| API | `/api/v1/publications` |
| Data | Faculty profiles, Google Scholar / SerpAPI sync, patents, exports |
| Maintenance | `data/assets/faculty_master.csv`, scheduler in [MAINTENANCE.md](MAINTENANCE.md) |

### Faculty affiliations (labs / centres / groups)

- Source file: `data/assets/Links.txt`
- Synced to `affiliations` and `faculty_affiliations` tables on API startup and when viewing affiliations
- Removing an entry from `Links.txt` removes it from the database on next sync

## BTP / IP projects

| Item | Detail |
|------|--------|
| UI | `/projects` (BTP/IP tab) |
| API | `/api/v1/projects` |
| Features | Import template, filters, SDG tagging (embedding model), PDF export |
| SDG | `ENABLE_SDG_LLM=false` recommended for manual review |

## ECE / EVE projects

| Item | Detail |
|------|--------|
| UI | `/projects` (ECE/EVE tab), analytics sub-panel |
| API | `/api/v1/ece-eve-projects` |
| Data | Subset of BTP/IP projects where branch is ECE or EVE |
| Sync | Rebuilt from `projects` table on BTP/IP import refresh |

Analytics group by **semester** tags (not admission year).

## Awards

| Item | Detail |
|------|--------|
| UI | `/awards` |
| API | `/api/v1/awards` |

## Notifications

| Item | Detail |
|------|--------|
| UI | Admin send notifications |
| API | `/api/v1/notifications` |

## Storage

Upload and result paths: [STORAGE.md](STORAGE.md)

## API documentation

With backend running: `http://<host>:8001/api/docs` (Swagger UI).
