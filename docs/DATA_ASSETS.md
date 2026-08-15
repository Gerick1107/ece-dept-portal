# Data assets (`data/assets/`)

**This folder is not in Git** (confidential departmental data). A fresh `git clone` will **not** include the Excel/CSV files the portal needs at runtime. You must **manually copy or restore** them onto every machine (laptop, testing server, institute server).

If you see errors like:

> CO-PO mapping file not found at `/data/assets/default_mapping.xlsx`

that is **expected** until `data/assets/` is populated. The app cannot invent department mapping / faculty CSVs from Git.

## How to obtain the files

| Source | When |
|--------|------|
| Secure copy from a maintainer’s machine (`scp -r data/assets …`) | First setup on a new server |
| Restore from restic / institute backup | After a crash or new host |
| Shared institute storage / encrypted bundle | Ongoing handoff |

See also [SERVER_SETUP.md](SERVER_SETUP.md) (manual copy checklist) and [BACKUP_RESTORE.md](BACKUP_RESTORE.md).

## Required layout

Place these files in `data/assets/` (create the folder if missing):

| File | Used by |
|------|---------|
| `default_mapping.xlsx`, `indirect.xlsx` | CO-PO generator (missing → red banner on CO-PO page) |
| `faculty_master.csv` | Publications |
| `Links.txt` | Faculty affiliations |
| `faculty_awards.csv` | Awards |
| `faculty_resource_person_events.csv` | Contributions — Resource Person |
| `faculty_mooc_development.csv` | Contributions — MOOC |
| `department_fdp_events.csv` | Contributions — Dept FDPs |
| `faculty_student_project_support.csv` | Contributions — Student projects |
| `faculty_collaborations.csv` | Contributions — Collaborations |
| `faculty_memberships.csv` | Contributions — Memberships |
| `faculty_services.csv` | Contributions — Faculty Services |
| `phd_students.csv` | Contributions — PhD Students |
| `course_allocations.csv` | Course allocation |
| `course_catalog.csv` | Course catalog (admin) |
| `course_code_aliases.csv` | Course code resolution |
| `faculty_name_aliases.csv` | Faculty name resolution |
| `non_faculty_placeholders.csv` | Placeholder faculty rows |
| `Monsoon YYYY.csv`, `Winter YYYY.csv` (or `WinterYYYY.csv`) | Historical CO-PO attainment for analytics backfill (`backend/scripts/backfill_legacy_copo.py`) |

Admin UI edits for contributions and allocations **write back** to the CSVs in this folder.

**Budget** data lives only in MySQL (`budget_income`, `budget_expenses`, `budget_inventory`); there is no budget CSV in `data/assets/`.

## Setup

**Local dev:** Copy from your team’s canonical bundle or restore from MySQL after import (DB is source of truth once synced; CSVs are re-exported on some operations).

**Docker:** The compose file mounts `./data/assets` → `/data/assets` on the backend. Populate the **host** folder before (or right after) `docker compose up`. Use a **writable** mount if admins edit data through the portal.

**Backups:** Include `data/assets/` in server backups alongside MySQL dumps.
