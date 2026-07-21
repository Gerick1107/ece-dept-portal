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

---

## CO-PO attainment

| Item | Detail |
|------|--------|
| UI | `/copo/*` (evaluate, compare, bulk, archives, generator) |
| API | `/api/v1/copo` |
| Engine | `backend/app/copo/engine/legacy_engine.py` |
| Inputs | Consolidated marks Excel, UG/PG CO-PO mapping |
| Outputs | Result Excel, JSON snapshot in MySQL, download tokens |

Workflow: [WORKFLOW_A.md](WORKFLOW_A.md)

---

## Courses

| Item | Detail |
|------|--------|
| API | `/api/v1/courses` |
| Purpose | Course catalogue used across CO-PO and insights |

---

## Course allocation

| Item | Detail |
|------|--------|
| UI | `/course-allocation` (faculty-wise), `/course-allocation/courses` (course-wise), `/course-allocation/faculty/:id`, `/course-allocation/course/:id` |
| Admin only | `/course-allocation/catalog` (Course Catalog) |
| API | `/api/v1/course-allocation` |
| CSV | `course_allocations.csv`, `course_catalog.csv`, `course_code_aliases.csv`, `faculty_name_aliases.csv`, `non_faculty_placeholders.csv` |

**Features:**

- **Faculty-wise** and **course-wise** allocation views with expandable tables
- Filters: **by semester**, **by academic year** (`YYYY-YYYY` or `YYYY-YY`), or **all data**
- Semesters listed newest-first within each group
- Dashboard summary widget (faculty teaching, UG/PG, core/elective, first-year counts)
- Faculty and course drill-in history / analytics pages
- Admin: upload XLSX, resolve unmatched faculty names, **add / edit / delete** allocation rows (both views), edit catalog entries
- Mutations write back to `course_allocations.csv`; both views read the same allocation rows
- Export allocations to Excel

Faculty and HOD see **Allocations** only; **Course Catalog** is hidden from faculty nav and route-guarded to admin.

---

## Budget

| Item | Detail |
|------|--------|
| UI | `/budget/accumulated-income`, `/budget/expenditure-budget`, `/budget/inventory` (also `/modules/budget` hub) |
| API | `/api/v1/budget` |
| Tables | `budget_income`, `budget_expenses`, `budget_inventory` (migration `033_budget_module`) |
| Invoices | PDF uploads under `storage/uploads/budget-invoices/` |

**Tabs:**

| Tab | Purpose |
|-----|---------|
| Accumulated Income | Budget heads by financial year — approved amount, utilised, remaining; optional invoice PDF |
| Expenditure Budget | Expense heads, utilisation, vendor, status, invoices |
| Inventory | Purchased items, category, quantity on hand / issued, location, invoices |

**Access:** any authenticated user can **read**; **create / update / delete** and invoice upload require **HOD** (or admin if granted that role). Seed rows for the current financial year are inserted by migration `033` on first `alembic upgrade head`.

---

## Faculty contributions (Analytics)

| Item | Detail |
|------|--------|
| UI | `/contributions` (under **Analytics** nav) |
| API | `/api/v1/contributions/{resource}` |
| Legacy redirect | `/fdps` → `/contributions` |

**Sub-tabs** (each backed by a CSV in `data/assets/`):

| Tab | API resource | CSV |
|-----|--------------|-----|
| Resource Person (STTP/FDP) | `resource-person-events` | `faculty_resource_person_events.csv` |
| MOOC / SWAYAM Development | `mooc-development` | `faculty_mooc_development.csv` |
| Dept. Organized FDPs/STPs | `department-fdp-events` | `department_fdp_events.csv` |
| Student Project Support | `student-project-support` | `faculty_student_project_support.csv` |
| Internships / Collaborations | `collaborations` | `faculty_collaborations.csv` |
| Professional Memberships | `memberships` | `faculty_memberships.csv` |
| Faculty Services | `faculty-services` | `faculty_services.csv` |
| PhD Students | `phd-students` | `phd_students.csv` |

**Features:** search, year filters, faculty filter, unmatched-faculty panel, admin add/edit/delete, Excel export, faculty name resolution. UI mutations write back to CSV for supported resources.

---

## Faculty awards

| Item | Detail |
|------|--------|
| UI | `/awards` |
| API | `/api/v1/awards` |
| CSV | `data/assets/faculty_awards.csv` |

See [MAINTENANCE.md](MAINTENANCE.md) for CSV sync behaviour.

---

## Publications

| Item | Detail |
|------|--------|
| UI | `/publications/faculty`, `/publications/search`, `/publications/student`, `/publications/exports`, `/publications/admin` |
| API | `/api/v1/publications` |
| Data | Faculty profiles, Google Scholar / SerpAPI sync, patents, exports, student Excel list |
| Maintenance | `faculty_master.csv`, Faculty Admin UI, `ENABLE_SCHEDULER` — [MAINTENANCE.md](MAINTENANCE.md) |

**Features:**

- Faculty profile tabs: Publications, Journals, Conferences, **Book Chapters** (Scholar `book` field), **Books** (manual `is_manual_book` only), **Preprints & Unlisted** (arXiv or empty venue), Patents
- Search by **title** or **venue** on faculty profiles and global search
- Faculty + admin can **edit** publication metadata (venue/pages/volume/…); edited fields are stored in `manual_overrides` and skipped by future sync/enrichment
- Faculty + admin can **delete** with double confirm; rows are tombstoned in `blocked_publications`
- Links to `repository.iiitd.edu.in` are purged and never re-ingested
- **Student Publications** (`/publications/student`): shared table, Excel template/import, dynamic columns, admin add/delete
- **Faculty Admin** (`/admin/faculty`): add faculty through UI → DB + `faculty_master.csv` + directory

### Faculty affiliations

- Source: `data/assets/Links.txt`
- Synced on API startup and affiliations page load

---

## Projects and Theses

| Item | Detail |
|------|--------|
| UI | `/projects` (Projects and Theses tab) |
| API | `/api/v1/projects` |
| Features | Import template, filters, SDG tagging, PDF export |

---

## ECE / EVE projects

| Item | Detail |
|------|--------|
| UI | `/projects` (ECE/EVE tab) |
| API | `/api/v1/ece-eve-projects` |
| Sync | Rebuilt from `projects` on Projects and Theses import |

---

## Meeting minutes

| Item | Detail |
|------|--------|
| UI | `/senate-minutes`, `/ece-faculty-meets`, `/aac-meetings`, `/ugc-meetings`, `/pgc-meetings` |
| Nav | **Minutes** dropdown |
| API | `/api/v1/documents/{type}` |
| Storage | `backend/documents/` or `DOCUMENTS_DIR` |

**Features:** year-grouped PDF lists, admin upload (PDF), dual agenda/minutes files per meeting where applicable, multi-turn RAG Q&A scoped per document set (local Ollama).

---

## Notifications & requirement tracker

| Item | Detail |
|------|--------|
| Faculty UI | `/notifications` |
| Admin UI | `/admin/notifications`, `/admin/requirement-tracker` |
| API | `/api/v1/notifications` |

### Sending notifications (admin)

- Use a **template** to link a message to a **requirement type** (updates Requirement Tracker to red)
- Initial delivery: portal notification + email (when `SMTP_ENABLED=true`)
- Optional **automatic reminders** at a chosen interval (days/weeks/minutes for testing)

### Requirement tracker (admin)

Matrix of faculty × requirement types with colour states:

| Colour | Meaning |
|--------|---------|
| Grey | Not requested |
| Red | Sent, unread |
| Yellow | Read / replied (text only) — pending admin review |
| Green | Fulfilled (reply with attachment, or admin override) |

Requirement types: upcoming semester courses, yearly report, new awards, new FDPs, verify SDGs, CO-PO attainment.

### Faculty replies

- Faculty open a notification and can **reply with text** and optional **file attachment** (≤ 10 MB)
- Reply **with attachment** → tracker turns **green** automatically
- Reply **text only** → tracker turns **yellow** (read, awaiting review)
- Admins see replies in notification detail view

### Auto-reminders

Controlled separately from publication scraping:

| Variable | Default | Purpose |
|----------|---------|---------|
| `ENABLE_REQUIREMENT_REMINDERS` | `true` | Background reminder job |
| `REQUIREMENT_REMINDER_POLL_MINUTES` | `1` | How often the job checks for due reminders |
| `ENABLE_SCHEDULER` | `false` | **Only** monthly publication gap-fill (Scholar/SerpAPI) |

**Behaviour:**

- Reminders repeat at the configured interval until the tracker cell is **green**
- With **SMTP enabled**: follow-up reminders are **email only**
- With **SMTP disabled** (local dev): reminders appear as **portal notifications**
- Reading the original notification moves red → yellow; reminders continue until green

---

## Analytics

| Item | Detail |
|------|--------|
| UI | `/analytics` |
| API | `/api/v1/analytics` |
| Data | CO-PO snapshots, projects, publications KPIs |

---

## LLM insights

| Item | Detail |
|------|--------|
| UI | `/llm-insights` |
| API | `/api/v1/llm-insights` |
| Provider | Local (Ollama), offline only; see root README |

---

## Storage

Upload and result paths: [STORAGE.md](STORAGE.md)

---

## API documentation

Development: `http://<host>:8001/api/docs` (Swagger). Disabled when `APP_ENV=production`.
