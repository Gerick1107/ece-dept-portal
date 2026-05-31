from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.projects.models.entities import ProjectUpload
from app.projects.schemas.project import ProjectCreate
from app.projects.services.faculty_resolver import resolve_faculty_by_name
from app.projects.services.file_manager import save_project_upload
from app.projects.services.project_service import _normalize_type, create_project
from app.projects.services.sdg_queue import enqueue_sdg_tags
from app.projects.utils.column_mapping import cell_str, map_headers, require_columns


def _load_dataframe(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path, engine="openpyxl")
    raise ValueError("Unsupported file type — use .csv, .xlsx, or .xls")


def _split_students(raw: str) -> list[str]:
    if not raw:
        return []
    for sep in [";", "|", "\n"]:
        if sep in raw:
            return [p.strip() for p in raw.split(sep) if p.strip()]
    if "," in raw:
        return [p.strip() for p in raw.split(",") if p.strip()]
    return [raw.strip()]


def _is_blank_row(row, mapping: dict[str, str]) -> bool:
    checks = ["project_title", "faculty", "semester", "project_type"]
    for key in checks:
        if key not in mapping:
            continue
        if cell_str(row[mapping[key]]):
            return False
    return True


def import_projects_file(
    db: Session,
    file_bytes: bytes,
    filename: str,
    uploaded_by: int | None,
    *,
    auto_sdg: bool = True,
) -> dict:
    stored_path, _stored_name = save_project_upload(filename, file_bytes)
    tmp = Path(stored_path)
    try:
        frame = _load_dataframe(tmp)
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        raise ValueError(f"Could not read spreadsheet: {exc}") from exc

    if frame.empty:
        raise ValueError("Spreadsheet has no data rows")

    mapping = map_headers([str(c) for c in frame.columns])
    missing = require_columns(mapping)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    upload = ProjectUpload(
        filename=filename,
        filepath=stored_path,
        uploaded_by=uploaded_by,
        record_count=0,
    )
    db.add(upload)
    db.flush()

    errors: list[str] = []
    imported = 0
    skipped = 0
    total_rows = len(frame)
    sdg_queued_ids: list[int] = []

    for idx, row in frame.iterrows():
        row_num = int(idx) + 2
        if _is_blank_row(row, mapping):
            skipped += 1
            continue
        try:
            title = cell_str(row[mapping["project_title"]])
            ptype = cell_str(row[mapping["project_type"]])
            faculty_raw = cell_str(row[mapping["faculty"]])
            semester = cell_str(row[mapping["semester"]])
            if not title or not ptype or not faculty_raw or not semester:
                raise ValueError("project_title, project_type, faculty, and semester are required")

            faculty = resolve_faculty_by_name(db, faculty_raw)
            co_guide = cell_str(row[mapping["co_guide"]]) if "co_guide" in mapping else ""
            students_raw = cell_str(row[mapping["students"]]) if "students" in mapping else ""
            status = cell_str(row[mapping["status"]]) if "status" in mapping else "Pending"
            credit = cell_str(row[mapping["credit"]]) if "credit" in mapping else None
            grade = cell_str(row[mapping["grade"]]) if "grade" in mapping else None

            body = ProjectCreate(
                project_title=title,
                project_type=_normalize_type(ptype),
                semester=semester,
                faculty_id=faculty.id,
                co_guide=co_guide or None,
                status=status or "Pending",
                credit=credit or None,
                grade=grade or None,
                students=_split_students(students_raw),
            )
            project = create_project(db, body, upload_batch_id=upload.id)
            imported += 1
            if auto_sdg:
                sdg_queued_ids.append(project.id)
        except Exception as exc:
            errors.append(f"Row {row_num}: {exc}")

    upload.record_count = imported
    db.commit()
    sdg_queued = 0
    if auto_sdg and sdg_queued_ids:
        sdg_queued = enqueue_sdg_tags(sdg_queued_ids)
    return {
        "upload_id": upload.id,
        "imported": imported,
        "total_rows": total_rows,
        "skipped_rows": skipped,
        "sdg_queued": sdg_queued,
        "errors": errors,
    }


def build_template_bytes() -> bytes:
    columns = [
        "Project Topic",
        "Project Type",
        "Faculty",
        "Co Guide",
        "Students",
        "Semester",
        "Status",
        "Credit",
        "Grade",
    ]
    sample = pd.DataFrame(
        [
            {
                "Project Topic": "Smart Irrigation System using IoT",
                "Project Type": "BTP",
                "Faculty": "Prof. Example Faculty",
                "Co Guide": "",
                "Students": "Student A; Student B",
                "Semester": "Winter 2026",
                "Status": "Approved",
                "Credit": "8",
                "Grade": "A",
            }
        ],
        columns=columns,
    )
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        sample.to_excel(writer, index=False, sheet_name="projects")
    return output.getvalue()
