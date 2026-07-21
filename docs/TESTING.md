# Testing

## Backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

Current automated coverage is intentionally narrow (documents/RAG, CO-PO purge, awards helpers, publication URL/venue filters). Add tests next to the behavior you change under `backend/tests/`.

Useful targeted runs:

```powershell
python -m pytest tests/test_publication_filters.py -q
python -m pytest tests/test_copo_purge_results.py -q
```

## Frontend

There is no Jest/Vitest suite yet. Minimum check before merge:

```powershell
cd frontend
npm run build
```

(`npm run build` runs `tsc -b` then Vite production build.)

## Manual smoke checklist (handoff)

1. Login as admin and faculty.
2. Publications → Faculty Directory → open a profile:
   - tabs: Publications, Journals, Conferences, Book Chapters, Books, Preprints & Unlisted, Patents
   - search by title and venue
   - Edit a venue field; sync must not overwrite it
   - Delete with double confirm; sync must not re-add
3. Publications → Student Publications: template download, import, add, delete (admin).
4. Admin → Faculty Admin: add a faculty row; confirm directory + `faculty_master.csv`.
5. Projects and Theses: create project, SDG generate/accept/reject/regenerate.
6. CO-PO Generator: question paper without COs → warnings, not hallucinated COs; bonus marks scaled in Excel.
7. Course Allocation: admin add/edit/delete; course-wise and faculty-wise stay consistent.
