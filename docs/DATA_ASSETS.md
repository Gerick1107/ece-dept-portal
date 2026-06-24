# Data assets (`data/assets/`)

**This folder is not in Git.** It holds departmental CSV/Excel files and `Links.txt` used at runtime. Copy or restore them on each machine from a secure source (SQL dump, shared institute storage, or encrypted transfer between maintainers).

## Required layout

Place these files in `data/assets/` (create the folder if missing):

| File | Used by |
|------|---------|
| `default_mapping.xlsx`, `indirect.xlsx` | CO-PO generator |
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

Admin UI edits for contributions and allocations **write back** to the CSVs in this folder.

## Setup

**Local dev:** Copy from your team’s canonical bundle or restore from MySQL after import (DB is source of truth once synced; CSVs are re-exported on some operations).

**Docker:** Mount the host folder into the container (see [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)). Use a **writable** mount if admins edit data through the portal.

**Backups:** Include `data/assets/` in server backups alongside MySQL dumps.
