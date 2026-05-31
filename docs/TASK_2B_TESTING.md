# Task 2B — Testing instructions

## Prerequisites

1. Local MySQL running with migrations through **005**:
   ```powershell
   cd backend
   python -m alembic upgrade head
   pip install -r requirements.txt
   ```
2. SDG AI tagging is **off by default** (`ENABLE_SDG_LLM=false`). Use manual SDG checkboxes unless testing LLM.
3. Faculty directory must contain supervisors (import via Publications → admin CSV if empty).

## Backend smoke tests

```powershell
cd backend
python -c "from app.main import app; print('OK', app.title)"
python scripts/generate_project_template.py
```

## Publications exports

1. Log in as **admin**.
2. Open **Publication Exports**.
3. Export CSV / Excel / PDF with faculty and/or year filters.
4. Confirm exported files **do not** contain a DOI column.
5. Use scope **Faculty-wise** with Excel for multi-sheet output.

## BTP/IP projects

1. Open **BTP / IP Projects** from the nav bar.
2. **Download template** — fill with real faculty names from the directory.
3. **Import** the spreadsheet (admin).
4. Verify table columns: Sl No, Semester, Project Topic, Type, Faculty, Co Guide, Students, SDGs, Status, Credit, Grade.
5. Use filters (faculty, semester, SDG, grade, topic search).
6. **Export** filtered results as CSV, Excel, or PDF.
7. **SDGs** → **Edit SDGs** → select checkboxes → **Save SDGs** (empty selection clears SDGs).
8. **Add / Edit / Delete** project manually (admin). New rows appear in **id order** (sequential in the table).

## Data & Archives

1. Admin → **Data & Archives**.
2. CO-PO sections unchanged.
3. **Project uploads** section lists import files with Download / Delete.

## API reference (prefix `/api/v1`)

| Method | Path |
|--------|------|
| GET | `/projects`, `/projects/search` |
| GET | `/projects/template` |
| POST | `/projects/import` |
| POST | `/projects` |
| PUT | `/projects/{id}` |
| DELETE | `/projects/{id}` |
| POST | `/projects/{id}/generate-sdgs` |
| POST | `/projects/{id}/accept-sdgs` |
| POST | `/projects/{id}/reject-sdgs` |
| POST | `/projects/{id}/edit-sdgs` |
| GET | `/projects/export?format=csv\|xlsx\|pdf` |
| GET | `/publications/exports?format=csv\|xlsx\|pdf&scope=all\|faculty\|year` |
| GET | `/projects/settings` |
| POST | `/auth/forgot-password` |
| POST | `/auth/users/{id}/deactivate` |
| POST | `/auth/users/{id}/activate` |
| DELETE | `/auth/users/{id}` (remove profile) |

## User management

1. Admin → **Users** → create test faculty account.
2. **Deactivate** → user cannot log in; data unchanged.
3. **Activate** → login works again.
4. **Remove profile** → user disappears from list; CO-PO data remains; same email can be registered again.
5. Login page → enter valid email → **Forgot password?** (SMTP required).
