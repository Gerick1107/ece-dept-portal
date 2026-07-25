# Admin User Manual — ECE Department Smart Portal

Complete navigation guide for **admin** accounts. Use this as the department reference for every portal feature you administer or use.

**Related:** [Faculty User Manual](USER_MANUAL_FACULTY.md) · [User management](USER_MANAGEMENT.md) · [Modules](MODULES.md) · [Deployment](DEPLOYMENT.md) · [Maintenance](MAINTENANCE.md)

---

## 1. Roles

| Role in DB | Display | Access |
|------------|---------|--------|
| `admin` | Admin | Full portal + **Admin** menu |
| `hod` | **Faculty · HoD** (Users page) | Faculty-scoped data + HoD privileges (budget write, lab manage, feedback email CC). Only one at a time |
| `faculty` | Faculty | Own linked data; Feedback; Notifications inbox; most tools below |

Create accounts as **Faculty** or **Admin** only. Assign HoD later with **Mark HoD** on the Users list.

### Faculty data scoping (critical)

Personal slices (projects, courses, awards, contributions, own publications edit scope, etc.) use **`users.faculty_id` → faculty directory**, not email and not display-name matching.

When replacing temporary emails with institutional accounts:

1. Create the account (real email + password).
2. **Link to faculty directory** via the dropdown on create or in the Users table.
3. Name spelling differences do not matter once the correct directory person is selected.
4. Leave the link empty for staff who should not inherit a faculty member’s private data.

---

## 2. Full navigation map

### Top-level (everyone, unless noted)

| Nav | Paths | Notes |
|-----|-------|--------|
| Dashboard | `/dashboard` | Module shortcuts |
| Feedback | `/feedback` | Faculty submit; admin resolve |
| CO-PO Attainment | `/copo`, `/copo/compare`, `/copo/bulk`, `/copo/results/:id` | Generator / Compare / Bulk |
| Publications | `/publications/faculty`, `/search`, `/student`, `/exports` | Directory, search, student list, exports |
| Projects and Theses | `/projects` | Main + ECE/EVE tabs |
| Budget | `/budget/accumulated-income`, `/expenditure-budget`, `/inventory` | Read all; write HoD/admin |
| Course Allocation | `/course-allocation`, `/course-allocation/courses`, `/course-allocation/catalog` | Catalog = **admin only** |
| Minutes | `/all-meetings`, `/senate-minutes`, `/ece-faculty-meets`, `/aac-meetings`, `/ugc-meetings`, `/pgc-meetings` | Browse + RAG; admin upload |
| Analytics | `/awards`, `/contributions`, `/analytics` | Awards, Contributions, Dashboard |
| LLM Insights | `/llm-insights` | Local Ollama insights |
| Notifications | `/notifications` | **Faculty inbox only** (hidden for admin) |
| Moderation | `/moderation`, `/moderation/courses/:id` | Papers + grading criteria |
| Lab Seating Capacity | `/labs` | View all; manage HoD/admin |
| Profile | `/profile` | Password change |

### Admin menu (admin only)

| Page | Path |
|------|------|
| Publications Admin | `/publications/admin` |
| Faculty Admin | `/admin/faculty` |
| Users | `/admin/users` |
| Send Notifications | `/admin/notifications` |
| Requirement Tracker | `/admin/requirement-tracker` |
| Data & Archives | `/admin/data` |

---

## 3. Dashboard

- Greets you by name and role.
- Module cards into CO-PO, Publications, Projects, Budget, Course Allocation, Minutes, Analytics, LLM Insights, Moderation, Labs, and Admin shortcuts.
- Unread notification badges apply to faculty inboxes; you send from **Admin → Send Notifications**.

---

## 4. Profile

- Change portal password (current + new, min 8 characters).
- Faculty/HoD may be forced here after first login or password reset.

---

## 5. Admin → Users (`/admin/users`)

### 5.1 Create account

1. Email, full name, portal password (min 8).
2. Role: **Faculty** or **Admin** only (no HoD in the create dropdown).
3. Optional **Link to faculty directory** (names from the directory; if empty, add faculty under Faculty Admin / CSV sync, then refresh).
4. Optional welcome email (needs SMTP).
5. Faculty accounts must change password on first login.

### 5.2 User list actions

| Action | Effect |
|--------|--------|
| Role column | Admin, Faculty, or **Faculty · HoD** |
| Faculty link dropdown | Assign or clear directory link (no raw id text) |
| **Mark HoD** / **Clear HoD** | Only one HoD; previous HoD returns to Faculty |
| Deactivate / Activate | Block or restore login |
| Remove | Anonymize profile; CO-PO history kept by internal user id; email can be reused |

You cannot deactivate/remove your own account or the last remaining admin.

---

## 6. Feedback (`/feedback`)

1. Faculty submit free-text feedback.
2. Admins see faculty name, email, timestamp, message.
3. **Mark resolved / unresolved**; faculty see that status on their list.
4. On submit (SMTP on): email alerts go to all active **admins** and the **HoD**.

Admins do not submit feedback; they only review it.

---

## 7. Admin → Send Notifications (`/admin/notifications`)

### 7.1 Templates

**Built-in** (each linked to a Requirement Tracker column):

- Upcoming Semester Course Details  
- Yearly Report Submission  
- New Awards Update  
- New FDPs Update  
- Verify Project SDGs (Projects and Theses)  
- CO-PO Attainment Data  

**+ Custom template:** enter label, subject, body → saved and **automatically adds a Requirement Tracker column**. Selecting any template fills subject/body and sets `requirement_type`.

### 7.2 Recipients

- Multi-select faculty/HoD portal users; **select all faculty**.
- Optional extra emails and/or Excel of emails (email-only; no portal profile / no tracker cell).
- Option to skip portal recipients (email-only send).

### 7.3 Reminders

- Off, or presets (1 day … 2 weeks), or custom interval (minutes/hours/days/weeks, capped).
- Reminders repeat until the tracker cell is **green**.
- SMTP on → reminder emails; SMTP off → portal reminder notifications (local/dev).

### 7.4 Attachments and history

- Attach files to the outgoing message.
- Review past sends and per-recipient read/email status and replies.

---

## 8. Admin → Requirement Tracker (`/admin/requirement-tracker`)

Matrix: each faculty/HoD user × each requirement type (built-in + custom).

| Colour | Meaning |
|--------|---------|
| Grey | Not requested |
| Red | Sent / unread |
| Yellow | Read or text reply — pending |
| Green | Fulfilled (reply with attachment, or admin override) |

Click a cell to set status manually. Search faculty by name/email. Sending a templated notification sets recipients to **red**.

---

## 9. Admin → Faculty Admin (`/admin/faculty`)

Add faculty to the directory (required fields match `faculty_master.csv`):

- Name *, Google Scholar ID *, join year *
- Optional: designation, department (default ECE), leave year, photo URL, profile link  

On save: database + `faculty_master.csv` + Faculty Directory update. New people appear in Users → faculty link dropdown and publication sync.

Edit/deactivate of existing directory rows is handled via directory/maintenance processes as documented in [MAINTENANCE.md](MAINTENANCE.md) if not shown on this page.

---

## 10. Admin → Publications Admin (`/publications/admin`)

### 10.1 Sync & dates

- **Sync All Publications** — SerpAPI Scholar scrape for active faculty (pubs + patents); fills exact dates for new rows via publisher/Crossref. Confirm before running (API cost).
- **Backfill Missing Dates** — fill exact dates for pubs that only have year/year-month (no SerpAPI). Background job.

### 10.2 Custom publication columns

- Add column: label, source keys, optional Crossref fallback field, enable/disable.
- Optional **Suggest sources (LLM)** for mapping ideas.
- **Backfill** missing custom-column values from publisher/Crossref.
- Delete column (stored values remain but stop exporting).

### 10.3 Scrape logs

Table of faculty, status, new pubs, started/completed, errors. **Refresh** after syncs.

---

## 11. Admin → Data & Archives (`/admin/data`)

| Section | Actions |
|---------|---------|
| Evaluation runs | **Archive** (copy Excel to `storage/archives/`, clear live result) · **Delete** run |
| Marks uploads | **Delete** upload rows |
| Result archives | **Delete** archived copies |
| Project uploads | **Download** / **Delete** Projects-and-Theses import files |
| Danger | **Purge all CO-PO data** (uploads, runs, archives, files — irreversible) |

---

## 12. CO-PO Attainment

Same three tools as faculty; you see department-wide activity and clean up via Data & Archives.

### 12.1 CO-PO Generator (`/copo`)

End-of-semester **Workflow A** — one consolidated marks Excel per course:

1. Select or add the **course**.
2. Ensure department **CO-PO mapping** for that course is available.
3. Upload one consolidated marks `.xlsx`.
4. Optional: year, section, programme/branch filters, indirect CO values.
5. Choose whether to save the run and/or delete server marks after success.
6. Generate → CO / PO / PSO tables + download result Excel.
7. Open results page for that run to review or delete evaluation data if permitted.

Download a marks **template** when the UI offers it.

### 12.2 Compare Evaluation (`/copo/compare`)

Single-course QA compare: upload mapping/marks as required → select course → labels/thresholds → side-by-side CO/PO tables.

### 12.3 Bulk Evaluation (`/copo/bulk`)

Multiple courses: optional shared mapping → per row input sheet + course + labels → **Add another course** → run and expand per-course tables.

Maintain the course list / mapping Excel used by the generator. Use **Analytics → CO-PO** for department insights.

---

## 13. Publications (shared + admin)

### 13.1 Faculty Directory (`/publications/faculty`)

Browse faculty cards/list; open profiles.

### 13.2 Faculty profile (`/publications/faculty/:id`)

Tabs such as: Publications, Journals, Conferences, Book Chapters, Books, Preprints & Unlisted, Patents. Affiliations at `/publications/faculty/:id/affiliations`.

**Faculty / HoD** edit/delete on their linked profile; **admin** can manage broadly.

- Edit metadata (venue, pages, volume, …) — stored in `manual_overrides`, skipped by later sync.
- Delete with confirmation — tombstoned so sync does not re-import.
- Links to `repository.iiitd.edu.in` are purged and not re-ingested.

### 13.3 Publications Search (`/publications/search`)

Global search (title/venue). Edit/delete when permitted.

### 13.4 Student Publications (`/publications/student`)

- Anyone signed in: browse/filter; **Download template**.
- **Admin only:** Import Excel, add rows, delete rows, manage dynamic columns as shown.

### 13.5 Publication Exports (`/publications/exports`)

- Export by faculty, years/dates, publications and/or patents.
- **Custom template:** upload headers → analyze (optional LLM) → map columns → compile download.

---

## 14. Projects and Theses (`/projects`)

### Tabs

1. **Projects and Theses** (BTP/IP-style)  
2. **ECE/EVE Projects** (mirrored from main projects where applicable)

### Filters and columns

Filter by search, guide, co-guide, type, semester (multi), course code/name, credit, etc.

**On-screen column order:** Serial → Semester → Title → Guide → Actions → SDGs → Course Code → Course Name → Co-Guide → Student Roll → Student Name → Credit.  
**Exports** keep the export schema (order may differ from the UI).

### SDGs

- Suggested SDGs when LLM is enabled.
- **Review SDGs / Edit SDGs** (Actions): select among all 17, accept/reject; reviewed rows highlight.
- **Regenerate** suggestions when available.
- **Bulk accept SDGs:** guide + semester range → preview → accept auto-suggested SDGs ≥ 50% confidence.

### Import / export / admin ops

| Action | Who |
|--------|-----|
| Download template | All |
| Import Excel (pick semester tag for the file) | Faculty + Admin |
| Export XLSX | All |
| Edit / Delete row | Admin |
| Add project (form) | Admin |
| Delete ALL projects | Admin |
| Bulk accept SDGs | Faculty + Admin (as shown) |

Manage import files under **Data & Archives → Project uploads**.

---

## 15. Budget

Anyone signed in can **view**. **Create / update / delete** and invoice PDFs require **HoD** (or admin where the UI grants write).

| Page | Content |
|------|---------|
| Accumulated Income | Heads by FY: approved / utilised / remaining; invoice PDFs |
| Expenditure Budget | Expense heads, vendor, status, utilisation, invoices |
| Inventory | Items, quantities, location, invoices |

Seed rows for the current financial year may appear after migration `033`.

---

## 16. Course Allocation

### 16.1 Faculty-Wise (`/course-allocation`) & Course-Wise (`/course-allocation/courses`)

- Scope: by **semester**, by **academic year**, or **all data**.
- Filters: **UG** and **PG** types separately — all / Core / Elective / Core/Elective.
- Summary widgets; for **Monsoon 2026+**, admin banner when **Number Of Registered Students** is still blank for some courses.
- Expand rows; open faculty/course detail analytics (`/course-allocation/faculty/:id`, `/course-allocation/course/:id`).
- **Admin:** Add / Edit / Delete allocations; set UG, PG, and **Number Of Registered Students**; resolve unmatched faculty names; upload Excel (preview → commit; import leaves registered students empty); export Excel.

Faculty cannot edit allocations or registered-student counts. Catalog is hidden from pure faculty nav and route-guarded to admin.

### 16.2 Course Catalog (`/course-allocation/catalog`) — admin only

Edit canonical course code, name, **UG** type, **PG** type. Changes propagate to matching allocation rows.

### 16.3 Columns

| Column | Meaning |
|--------|---------|
| **UG** | Core / Elective / Core/Elective (or blank) |
| **PG** | Same at PG level |
| **Number Of Registered Students** | Admin-only; blank after Excel import |

Mutations sync to `data/assets/` CSVs (`course_allocations.csv`, `course_catalog.csv`, aliases, …) per deployment config.

---

## 17. Minutes

| Page | Path |
|------|------|
| All Meetings | `/all-meetings` |
| Senate | `/senate-minutes` |
| ECE Faculty | `/ece-faculty-meets` |
| AAC | `/aac-meetings` |
| UGC | `/ugc-meetings` |
| PGC | `/pgc-meetings` |

Common features:

- Browse meetings by **year**.
- Download **agenda** and/or **minutes** PDFs.
- **Ask questions** (RAG) against that meeting type’s documents when the local LLM is up — multi-turn Q&A with sources.
- **Admin:** upload/replace PDFs; set title, meeting date, description. Dual-file meetings show both agenda and minutes when present.

---

## 18. Faculty Awards (`/awards`)

- Browse by faculty; filter search / year / exact year / faculty.
- Export Excel (optional year range and faculty selection).
- **Admin:** Add / Edit / Delete.
- Syncs with `faculty_awards.csv` (see Maintenance).

---

## 19. Faculty Contributions (`/contributions`)

Sub-tabs:

1. Resource Person (STTP/FDP)  
2. MOOC / SWAYAM Development  
3. Dept. Organized FDPs/STPs  
4. Student Project Support  
5. Internships / Collaborations  
6. Professional Memberships  
7. Faculty Services  
8. PhD Students  

Per tab: search, year, faculty filter, Excel export. **Admin:** add/edit/delete and resolve unmatched faculty names. Legacy `/fdps` → `/contributions`. CSV write-back under `data/assets/` for supported resources.

---

## 20. Analytics Dashboard (`/analytics`)

Tabs: **CO-PO**, **Projects**, **ECE/EVE Projects**, **Awards**, **Publications**.

Department KPIs, charts, and filtered tables for reporting.

---

## 21. LLM Insights (`/llm-insights`)

1. Select a course with stored evaluation data.  
2. Choose current and optional previous semester (and section if offered).  
3. Review assessment structure used for the prompt.  
4. **Generate** AI recommendations (local Ollama); cached insights may load automatically.  
5. Provider selector only if the deployment exposes it.

Requires the local LLM stack configured by IT.

---

## 22. Moderation (`/moderation`)

### Question papers

- List moderation courses; open `/moderation/courses/:courseId`.
- Faculty / HoD / Admin: **upload** papers.
- Admin: delete papers / manage courses as shown.

### Grade summary

- Define / edit **grading criteria** per course (faculty / HoD / Admin).
- Admin may have extra delete controls.

---

## 23. Lab Seating Capacity (`/labs`)

- View: name, location, faculty in charge, total / allotted / remaining seats, occupancy bar, remarks.
- Filter by faculty or search; summary KPIs.
- **Admin / HoD:** create and edit labs.
- **Admin:** delete labs.

---

## 24. SMTP-dependent features

Configure SMTP in `.env` / `.env.docker` for:

| Feature | Behaviour without SMTP |
|---------|-------------------------|
| Welcome email on user create | Account still created |
| Forgot-password temp password | Contact admin for manual reset |
| Notification emails + reminders | Portal notifications still work |
| Feedback alerts to admins + HoD | Feedback still stored in portal |

---

## 25. Operational checklist

| Task | Where |
|------|--------|
| Onboard faculty with real email | Users → create + faculty link |
| Appoint HoD | Users → Mark HoD |
| Request data from faculty | Send Notifications + Requirement Tracker |
| Review faculty issues | Feedback |
| Import teaching load | Course Allocation → upload + fill registered students |
| Maintain course master | Course Catalog |
| Import projects / SDGs | Projects and Theses |
| Scholar / directory | Faculty Admin + Publications Admin |
| Custom pub columns / sync | Publications Admin |
| CO-PO cleanup | Data & Archives |
| Meeting PDFs | Minutes pages |
| Awards / FDPs / memberships | Awards + Contributions |
| Lab seats | Lab Seating Capacity |
| Student publication sheet | Student Publications (admin import) |

### After deploy / schema changes

```powershell
cd backend
alembic upgrade head
```

Back up MySQL and `DATA_ASSETS` CSVs together ([BACKUP_RESTORE.md](BACKUP_RESTORE.md), [MAINTENANCE.md](MAINTENANCE.md)).

---

## 26. Troubleshooting

| Issue | Likely fix |
|-------|------------|
| Faculty see empty personal data | Set correct **faculty link** on Users |
| Faculty link dropdown empty | Directory empty — use Faculty Admin / CSV; refresh Users |
| Welcome / reset / feedback mail missing | `SMTP_ENABLED` and SMTP credentials |
| Tracker column missing for new request | Create **custom template** (auto-links) or use built-in |
| Course allocation reminder never shows | Only for **Monsoon 2026+** summary semesters |
| Registered students blank after import | Expected — edit each allocation |
| LLM / Minutes Q&A down | Ollama / provider config |
| Sync All uses many API calls | Confirm SerpAPI keys; watch Scrape Logs |
| Last admin cannot be removed | By design |

---

*End of Admin User Manual.*
