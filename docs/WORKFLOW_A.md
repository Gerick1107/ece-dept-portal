# Workflow A — End-of-semester consolidated upload

## Analysis: what was implemented before this change

| Layer | Workflow B (component-wise)? | Workflow A (consolidated)? |
|-------|------------------------------|----------------------------|
| **Computation (`legacy_engine.py`)** | No | **Yes** — always one Excel with all assessment columns |
| **Excel parser** | No | **Yes** — reads single sheet; columns = Quiz/MidSem/EndSem/etc. |
| **Database** | Naming looked like “sessions” (could imply many uploads) | One row per **final** upload; now tagged `upload_type=final_consolidated` |
| **API** | Two-step parse → evaluate felt like multiple steps | **Primary:** `POST /api/v1/copo/final-submit` (one shot) |
| **Frontend** | Upload-first without emphasizing “one final file” | **Course → mapping → one file → Generate** |

**Conclusion:** Computation was always Workflow A. The confusion came from API/UI splitting parse and evaluate, and DB naming—not from component-wise engine logic.

## Final faculty flow (Workflow A)

1. Login (portal email + password; not Gmail password)
2. Forgot password on login page emails a temporary password (SMTP required)
3. Change password if first login or after reset (Profile)
4. **Select course** (from department CO-PO mapping Excel)
5. **Upload one consolidated `.xlsx`** (all semester marks in columns)
6. Optional: programme/branch filters, indirect CO values
7. **Generate CO-PO results** → CO stats, PO/PSO, Excel report
8. Optional: remove raw marks from server after success (report kept in DB + archive)

## API map

| Purpose | Endpoint |
|---------|----------|
| Faculty submit (primary) | `POST /api/v1/copo/final-submit` |
| Preview file only | `POST /api/v1/copo/parse-students` |
| Download template | `GET /api/v1/copo/template` |
| Legacy single evaluate | `POST /api/v1/copo/evaluate` (still supported) |
| QA compare | `POST /api/v1/copo/evaluate/compare` |
| QA bulk compare | `POST /api/v1/copo/evaluate/bulk` |

## Database (unchanged tables, clearer semantics)

- `copo_marks_uploads` — one **final consolidated** file per submission (`upload_type`, `course_title`)
- `copo_evaluation_runs` — one attainment run per submission (`evaluation_type=final_consolidated`)
- `copo_result_archives` — exported Excel after optional marks cleanup
- `users.must_change_password` — faculty must change temp password

## Migration

```bash
cd backend
alembic upgrade head
python scripts/generate_marks_template.py
```

Revision `002` adds: `users.must_change_password`, `copo_marks_uploads.upload_type`, `copo_marks_uploads.course_title`.
