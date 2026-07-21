# Database & migrations

## Policy

- **Alembic** is the supported way to change schema on deployed servers.
- `Base.metadata.create_all()` runs on API startup as a safety net for brand-new tables in fresh DBs; it will **not** alter existing columns. Always ship a migration for column additions.
- MySQL 8 is required.

## Commands

```powershell
cd backend
alembic current
alembic history
alembic upgrade head
alembic downgrade -1   # only when you know the downgrade is safe
```

## Recent publications-related revisions

| Revision | Summary |
|----------|---------|
| `034_user_faculty_link` | `users.faculty_id` for scoped faculty logins |
| `035_publication_custom_columns` | Admin custom columns + `publications.custom_fields` |
| `036_publication_manual_overrides` | `manual_overrides`, `is_manual_book`, purge `repository.iiitd.edu.in` rows |
| `037_student_publications` | `student_publications` table |
| `038_sdg_ever_accepted` | `projects.sdg_ever_accepted` highlight flag |

## Important tables (publications)

| Table | Role |
|-------|------|
| `faculty` | Directory + Scholar IDs |
| `publications` | Papers/patents |
| `publication_faculty` | M2M links |
| `blocked_publications` | Tombstones for deleted papers (sync skip) |
| `publication_audit_logs` | Manual create/update/delete audit |
| `scrape_logs` | Sync progress/errors |
| `student_publications` | Separate student Excel-driven list |

## Faculty CSV mirror

`data/assets/faculty_master.csv` columns:

`id,name,designation,department,scholar_id,join_year,leave_year,photo_url,profile_link`

UI **Faculty Admin** and CSV import both update the DB; UI create/update also upserts the CSV via `faculty_master_csv.py`.
