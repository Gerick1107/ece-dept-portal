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
| UI | `/course-allocation`, `/course-allocation/faculty/:id` |
| Admin only | `/course-allocation/catalog` (Course Catalog) |
| API | `/api/v1/course-allocation` |
| CSV | `course_allocations.csv`, `course_catalog.csv`, `course_code_aliases.csv`, `faculty_name_aliases.csv`, `non_faculty_placeholders.csv` |

**Features:**

- Faculty-grouped allocation view with expandable course tables
- Filters: **by semester**, **by academic year** (`YYYY-YYYY` or `YYYY-YY`), or **all data**
- Dashboard summary widget (faculty teaching, UG/PG, core/elective, first-year counts)
- Faculty allocation history and analytics per person
- Admin: upload XLSX, resolve unmatched faculty names, edit catalog entries
- Export allocations to Excel

Faculty and HOD see **Allocations** only; **Course Catalog** is hidden from faculty nav and route-guarded to admin.

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
| UI | `/publications/*` |
| API | `/api/v1/publications` |
| Data | Faculty profiles, Google Scholar / SerpAPI sync, patents, exports |
| Maintenance | `faculty_master.csv`, `ENABLE_SCHEDULER` — [MAINTENANCE.md](MAINTENANCE.md) |

### Faculty affiliations

- Source: `data/assets/Links.txt`
- Synced on API startup and affiliations page load

---

## BTP / IP projects

| Item | Detail |
|------|--------|
| UI | `/projects` (BTP/IP tab) |
| API | `/api/v1/projects` |
| Features | Import template, filters, SDG tagging, PDF export |

---

## ECE / EVE projects

| Item | Detail |
|------|--------|
| UI | `/projects` (ECE/EVE tab) |
| API | `/api/v1/ece-eve-projects` |
| Sync | Rebuilt from `projects` on BTP/IP import |

---

## Meeting minutes

| Item | Detail |
|------|--------|
| UI | `/senate-minutes`, `/ece-faculty-meets`, `/aac-meetings`, `/ugc-meetings`, `/pgc-meetings` |
| Nav | **Minutes** dropdown |
| API | `/api/v1/documents/{type}` |
| Storage | `backend/documents/` or `DOCUMENTS_DIR` |

**Features:** year-grouped PDF lists, admin upload (PDF), dual agenda/minutes files per meeting where applicable, scoped LLM Q&A per document set.

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
| Provider | Groq (`GROQ_API_KEY`) |

---

## Storage

Upload and result paths: [STORAGE.md](STORAGE.md)

---

## API documentation

Development: `http://<host>:8001/api/docs` (Swagger). Disabled when `APP_ENV=production`.
