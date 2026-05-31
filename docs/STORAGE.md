# CO-PO storage and privacy

## Database tables

### `copo_marks_uploads`

| Column | Stored | Notes |
|--------|--------|-------|
| `storage_path` | Server path to uploaded marks `.xlsx` | Hard-deleted when cleanup runs |
| `parse_metadata` | JSON: CO list, programme counts, branch counts, `total_students` | **No roll numbers, names, or per-student marks** |
| `upload_type` | `final_consolidated`, `parsed_input`, `percentage_results`, etc. | Compare/bulk generated `*_CO_Percentage_Results.xlsx` use `percentage_results` |
| `original_filename` | Filename only | |

**Why two rows appeared before:** the generator auto-parsed marks via `POST /copo/parse-students` (creating a `parsed_input` row) and `POST /copo/final-submit` created a second `final_consolidated` row. Auto-parse on the generator now uses `persist=false` (no DB row). The delete checkbox removes **all** sibling upload rows for the same course/file plus the evaluation run.

### `copo_evaluation_runs`

| Column | Stored | Notes |
|--------|--------|-------|
| `result_summary` | JSON: aggregate CO/PO stats only | No student-level marks |
| `excel_result_path` | Path under `storage/results/` | Course-based name, e.g. `ADC_CO_PO_Percentage_Results.xlsx` |
| `scope_summary` | Programme/branch filter text | |

Compare and bulk workflows **do not** create evaluation runs (no DB persist).

### `copo_result_archives`

Optional snapshots of the **result Excel only** (not raw marks).

| When created | How |
|--------------|-----|
| Admin clicks **Archive** on **Data & Archives** (`POST /copo/admin/runs/{id}/archive`) | Copies Excel to `storage/archives/`, inserts archive row, clears marks upload, removes live file from `storage/results/` |
| Legacy API | `POST /copo/runs/{id}/archive-and-clear-marks` (same behaviour) |

If this table is empty, no archive action has been run yet. Normal evaluations only set `excel_result_path` on the run.

## Disk folders

| Folder | Purpose |
|--------|---------|
| `backend/storage/uploads/` | Incoming marks `.xlsx` only (course-based names, e.g. `ADC_final_consolidated_a1b2c3d4.xlsx`) |
| `backend/storage/results/` | Generated `*_CO_PO_Percentage_Results.xlsx` reports |
| `backend/storage/archives/` | Optional archived report copies |
| `data/assets/` | Default CO-PO mapping + indirect survey (canonical) |
| `data/templates/` | Faculty marks template |
| `data/samples/` | Sample course workbooks (BE, FW, ADC, etc.) — not used at runtime |

Stale files under `uploads/` and `results/` are removed after `FILE_MAX_AGE_SECONDS` (default 30 minutes) by the background cleanup thread.

## Portal UI: how to see data

### Evaluation runs & uploads (normal path)

1. Sign in as faculty.
2. **CO-PO Generator** → select course → upload consolidated marks → submit.
3. Unless **“Do not save to database”** is checked, a row appears in `copo_evaluation_runs` and one in `copo_marks_uploads`.
4. **Open saved results** (link after submit) loads aggregates from the DB — not raw marks.

### Archives (`copo_result_archives`)

There is **no automatic** archive on submit. To create an archive row:

1. Sign in as **admin**.
2. **Data & Archives** → Evaluation runs → **Archive** on a run that still has a result Excel (`has_excel`).
3. A file is copied to `storage/archives/` and a row is inserted; marks upload is cleared.

### Delete checkbox (faculty)

**“Delete all server data after successful processing”** after a successful run:

- Hard-deletes all related `copo_marks_uploads` rows (including old orphan parse rows for the same course).
- Deletes the `copo_evaluation_runs` row and any `copo_result_archives` rows/files.
- Leaves the result Excel on disk briefly so the immediate **Download Excel** link still works; the file is removed by the age-based cleanup job.

### Do not save to database (faculty)

Checkbox **“Do not save this run to the database”**: processing runs in memory/temp files only; nothing in `copo_evaluation_runs` or `copo_marks_uploads`. Download the Excel before leaving the page.

### Admin cleanup

**Data & Archives**: delete individual runs, uploads, or archives; **Purge all CO-PO data** wipes every row and linked file.

## Sample assets

Reference workbooks live in `data/samples/` (moved from project root). Runtime mapping uses `data/assets/default_mapping.xlsx` and `data/assets/indirect.xlsx`.
