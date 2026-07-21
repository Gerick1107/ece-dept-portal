# Maintenance guide

## Portal user accounts

See [USER_MANAGEMENT.md](USER_MANAGEMENT.md) for creating accounts, deactivate/activate, remove profile, and forgot password.

Ensure `SMTP_ENABLED=true` and SMTP settings in `backend/.env` for email features (welcome, reset, notifications, reminders).

---

## Publications module

### Adding a new faculty member

**Preferred:** Admin → **Faculty Admin** → fill the form (same fields as `faculty_master.csv`). This writes the DB row, upserts `data/assets/faculty_master.csv`, and shows the person in Faculty Directory / filters.

**Alternate:** Edit `faculty_master.csv` manually, then Admin → Publications → Import CSV, then Sync All Publications.

### Faculty member leaves

1. Set `leave_year` via CSV re-import or faculty update API/UI.
2. They appear under Former Faculty; publications are retained.

### Deleting / editing publications

- Delete (faculty or admin) double-confirms in the UI and inserts a `blocked_publications` tombstone so Scholar sync will not recreate the paper.
- Edit protects changed columns via `manual_overrides`. Title/authors/year/citations stay scrape-owned.
- Tick **Assign to Books** in the edit dialog to place a paper on the Books tab (Book Chapters remain Scholar-driven).

### Student publications

- UI: Publications → **Student Publications**
- Download template (Title, Authors, Years), import any wider Excel; extra headers appear automatically.
- Admin can add single rows or delete; all authenticated users can view/search.

### Monthly sync (hosted server)

1. Set `ENABLE_SCHEDULER=true` in `backend/.env`, restart backend.
2. APScheduler runs **publication gap-fill** on the 1st of each month at 02:00 UTC.

This flag does **not** control requirement reminders (see [Notifications & reminders](#notifications--requirement-reminders) below).

### Monthly sync (local)

Keep `ENABLE_SCHEDULER=false` and run Admin → Publications → Sync All Publications manually each month.

### SerpAPI

- Free tier: 250 searches/month.
- Update `SERP_API_KEY` in `backend/.env` as needed.

### Gap-fill CLI

```bash
cd backend
python scripts/scrape_gap_fill.py
```

---

## Faculty affiliations (`Links.txt`)

Research labs, centres, and groups: `data/assets/Links.txt` (local only — see [DATA_ASSETS.md](DATA_ASSETS.md)).

- Edit the file; sync runs on API startup and affiliations page load.
- Removing an entry removes it from the database on next sync.

---

## Faculty awards (CSV)

Source: `data/assets/faculty_awards.csv`.

Sync on Awards page load. Admin UI add/delete supported. See existing upsert/removal rules in CSV sync.

---

## Faculty contributions (CSV)

Multiple tabs under **Analytics → Faculty Contributions**. Each tab syncs from `data/assets/` on page load.

| CSV | Tab |
|-----|-----|
| `faculty_resource_person_events.csv` | Resource Person |
| `faculty_mooc_development.csv` | MOOC / SWAYAM |
| `department_fdp_events.csv` | Dept. FDPs/STPs |
| `faculty_student_project_support.csv` | Student Project Support |
| `faculty_collaborations.csv` | Internships / Collaborations |
| `faculty_memberships.csv` | Memberships |
| `faculty_services.csv` | Faculty Services |
| `phd_students.csv` | PhD Students |

**Admin UI** add/edit/delete for Faculty Services and PhD Students (and other tabs) writes back to the CSV on mutation.

**Unmatched faculty names** in CSV rows appear in an admin warning panel; use resolve-faculty or fix spelling / aliases in `faculty_name_aliases.csv`.

---

## Course allocation (CSV)

| File | Purpose |
|------|---------|
| `course_allocations.csv` | Semester-wise faculty–course assignments |
| `course_catalog.csv` | Master course list (codes, names, UG/PG, core/elective) |
| `course_code_aliases.csv` | Alternate codes → canonical catalog entry |
| `faculty_name_aliases.csv` | CSV spelling → faculty.id |
| `non_faculty_placeholders.csv` | “Not offered”, “TBD”, etc. |

- Sync on allocations page load; admin mutations write back to CSV.
- Admin can upload allocation XLSX for the current semester.
- **Course Catalog** edits are admin-only.

---

## Notifications & requirement reminders

### Sending

1. Admin → **Send Notifications** → pick a **template** (sets requirement type for the tracker).
2. Set **automatic reminders** interval (or Off).
3. Send to selected faculty or all.

### Reminder scheduler (separate from publication sync)

| Variable | Default | Effect |
|----------|---------|--------|
| `ENABLE_REQUIREMENT_REMINDERS` | `true` | Runs reminder background job |
| `REQUIREMENT_REMINDER_POLL_MINUTES` | `1` | Check frequency (minutes) |
| `ENABLE_SCHEDULER` | `false` | **Only** monthly publication scraping |

On backend start, look for log line: `Requirement reminder scheduler active (poll every N minute(s))`.

**Production:** keep `SMTP_ENABLED=true` so reminders go by email until the tracker is green.

**Local testing:** use a template + custom interval (e.g. 2 minutes). Without SMTP, reminders appear under faculty **Notifications**.

### Faculty replies

Faculty reply on `/notifications` with optional attachment. Attachment → green on tracker; text-only → yellow.

---

## Meeting PDFs

Confidential PDFs under `backend/documents/` (or `DOCUMENTS_DIR`):

```
backend/documents/senate-minutes/<year>/
backend/documents/ece-faculty-meets/<year>/
backend/documents/aac-meetings/<year>/
backend/documents/ugc-meetings/<year>/
backend/documents/pgc-meetings/<year>/
```

**Add:** Admin upload on the relevant Minutes page, or copy PDFs to disk and refresh.

Folders are in git; `*.pdf` is gitignored.

---

## Migrations

After pulling new code:

```bash
cd backend
python -m alembic upgrade head
```

Recent migrations include course allocation (`029`), faculty contributions expansions (`030`), notification replies (`031`), document embeddings (`032`), budget (`033`), user↔faculty link (`034`), publication custom columns (`035`), publication manual overrides / books flag (`036`), and student publications (`037`). See [DATABASE.md](DATABASE.md).

---

## Docker deployments

See [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md). Mount host `data/assets/` into the backend container (writable if using admin CSV write-back).
