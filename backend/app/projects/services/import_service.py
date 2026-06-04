from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.projects.models.entities import Project, ProjectUpload
from app.projects.schemas.project import ProjectCreate
from app.projects.services.faculty_resolver import cleaned_guide_display, match_ece_faculty
from app.projects.services.file_manager import save_project_upload
from app.projects.services.project_service import create_project, find_merge_candidate, merge_project
from app.projects.services.sdg_queue import enqueue_sdg_tags
from app.projects.utils.column_mapping import (
    DEPARTMENT_REQUIRED_FIELDS,
    cell_str,
    find_department_header_row_index,
    map_department_headers,
)
from app.projects.utils.course_name import normalize_course_name
from app.utils.name_utils import strip_name_prefix


def _excel_engine(data: bytes, suffix: str) -> str:
    """Pick reader engine from file magic bytes (handles .xls saved with .xlsx extension)."""
    if data[:2] == b"PK":
        return "openpyxl"
    if len(data) >= 8 and data[:4] == b"\xd0\xcf\x11\xe0":
        return "xlrd"
    if suffix == ".xlsx":
        return "openpyxl"
    if suffix == ".xls":
        return "xlrd"
    raise ValueError(
        "Unrecognized Excel format. Upload a valid .xlsx or .xls workbook (not a .zip archive)."
    )


def _read_excel_raw(data: bytes, engine: str) -> pd.DataFrame:
    try:
        return pd.read_excel(BytesIO(data), engine=engine, header=None)
    except Exception as primary_exc:
        alternate = "xlrd" if engine == "openpyxl" else "openpyxl"
        try:
            return pd.read_excel(BytesIO(data), engine=alternate, header=None)
        except Exception:
            raise primary_exc


def _frame_with_detected_headers(raw: pd.DataFrame) -> pd.DataFrame:
    header_row = find_department_header_row_index(raw)
    if header_row is None:
        return raw
    headers = [cell_str(v) or f"Column_{i}" for i, v in enumerate(raw.iloc[header_row].tolist())]
    frame = raw.iloc[header_row + 1 :].copy()
    frame.columns = headers
    frame = frame.dropna(how="all")
    frame.reset_index(drop=True, inplace=True)
    return frame


def _load_dataframe_from_bytes(data: bytes, filename: str) -> pd.DataFrame:
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        raw = pd.read_csv(BytesIO(data), header=None)
        header_row = find_department_header_row_index(raw)
        if header_row is not None:
            return _frame_with_detected_headers(raw)
        raw.columns = raw.iloc[0]
        return raw.iloc[1:].reset_index(drop=True)
    if suffix not in {".xlsx", ".xls"}:
        raise ValueError("Unsupported file type — use .csv, .xlsx, or .xls")
    engine = _excel_engine(data, suffix)
    raw = _read_excel_raw(data, engine)
    header_row = find_department_header_row_index(raw)
    if header_row is not None:
        return _frame_with_detected_headers(raw)
    # Template-style: first row is already the header
    frame = pd.read_excel(BytesIO(data), engine=engine)
    return frame


def _parse_credit(raw: str) -> float | None:
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _is_blank_row(row, mapping: dict[str, str]) -> bool:
    for key in ("title", "guide_name", "student_roll_no", "student_name"):
        col = mapping.get(key)
        if col and cell_str(row[col]):
            return False
    return True


def import_projects_file(
    db: Session,
    file_bytes: bytes,
    filename: str,
    uploaded_by: int | None,
    *,
    semester_tag: str,
    auto_sdg: bool = True,
) -> dict:
    if not semester_tag or not semester_tag.strip():
        raise ValueError("Semester tag is required (e.g. Monsoon 2024)")

    semester_tag = semester_tag.strip()
    try:
        frame = _load_dataframe_from_bytes(file_bytes, filename)
    except Exception as exc:
        raise ValueError(f"Could not read spreadsheet: {exc}") from exc

    stored_path, _stored_name = save_project_upload(filename, file_bytes)

    if frame.empty:
        raise ValueError("Spreadsheet has no data rows")

    mapping = map_department_headers([str(c) for c in frame.columns])
    missing = sorted(DEPARTMENT_REQUIRED_FIELDS - set(mapping))
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
    merged = 0
    skipped_ece = 0
    total_rows = len(frame)
    sdg_queued_ids: list[int] = []

    for idx, row in frame.iterrows():
        row_num = int(idx) + 2
        if _is_blank_row(row, mapping):
            continue
        try:
            title = cell_str(row[mapping["title"]])
            guide_raw = cell_str(row[mapping["guide_name"]])
            co_guide_raw = cell_str(row[mapping["co_guide"]]) if "co_guide" in mapping else ""
            roll_no = cell_str(row[mapping["student_roll_no"]])
            student_name = cell_str(row[mapping["student_name"]])
            course_code = cell_str(row[mapping["course_code"]])
            course_name_raw = cell_str(row[mapping["course_name"]]) if "course_name" in mapping else ""
            project_type = cell_str(row[mapping["project_type"]]) if "project_type" in mapping else ""
            credit_raw = cell_str(row[mapping["credit"]]) if "credit" in mapping else ""

            if not title or not guide_raw:
                raise ValueError("Title and Guide Name are required")

            faculty = match_ece_faculty(db, guide_raw, co_guide_raw or None)
            if not faculty:
                skipped_ece += 1
                continue

            guide_clean = cleaned_guide_display(faculty)
            co_guide_clean = strip_name_prefix(co_guide_raw) if co_guide_raw else None
            course_name = normalize_course_name(course_name_raw) if course_name_raw else None

            admission_year = cell_str(row[mapping["admission_year"]]) if "admission_year" in mapping else None
            program_definition = (
                cell_str(row[mapping["program_definition"]]) if "program_definition" in mapping else None
            )
            program_specialization = (
                cell_str(row[mapping["program_specialization"]])
                if "program_specialization" in mapping
                else None
            )

            existing = find_merge_candidate(db, title, guide_clean, course_code)
            if existing:
                merge_project(
                    existing,
                    semester_tag=semester_tag,
                    student_roll_no=roll_no,
                    student_name=student_name,
                )
                db.flush()
                merged += 1
                imported += 1
                if auto_sdg:
                    sdg_queued_ids.append(existing.id)
                continue

            body = ProjectCreate(
                project_title=title,
                project_type=project_type or "IP/IS/UR",
                semesters=semester_tag,
                faculty_id=faculty.id,
                co_guide=co_guide_clean,
                course_code=course_code or None,
                course_name=course_name,
                admission_year=admission_year or None,
                program_definition=program_definition or None,
                program_specialization=program_specialization or None,
                student_roll_nos=roll_no,
                student_names=student_name,
                credit=_parse_credit(credit_raw),
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
        "merged": merged,
        "total_rows": total_rows,
        "skipped_rows": skipped_ece,
        "sdg_queued": sdg_queued,
        "errors": errors,
    }


def build_template_bytes() -> bytes:
    columns = [
        "Sr. No.",
        "Admission year",
        "Program Definition",
        "Program Specialization",
        "Semester",
        "Project Type",
        "Course Code",
        "Course Name",
        "Credit",
        "Student Roll Number",
        "Student Name",
        "Guide Name",
        "Co-guide",
        "Title",
        "Grade",
        "Project status",
    ]
    sample = pd.DataFrame(
        [
            {
                "Sr. No.": 1,
                "Admission year": 2022,
                "Program Definition": "B.Tech",
                "Program Specialization": "ECE",
                "Semester": "(ignored — set at upload)",
                "Project Type": "Thesis",
                "Course Code": "BTP498",
                "Course Name": "B.Tech Project",
                "Credit": 8,
                "Student Roll Number": "2022241",
                "Student Name": "Example Student",
                "Guide Name": "Dr. Sujay Deb",
                "Co-guide": "",
                "Title": "Smart Irrigation System using IoT",
                "Grade": "(not stored)",
                "Project status": "(not stored)",
            }
        ],
        columns=columns,
    )
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        sample.to_excel(writer, index=False, sheet_name="projects")
    return output.getvalue()


def list_distinct_semester_tags(db: Session) -> list[str]:
    rows = db.scalars(select(Project.semesters)).all()
    tags: set[str] = set()
    for value in rows:
        if not value:
            continue
        for part in value.split(","):
            cleaned = part.strip()
            if cleaned:
                tags.add(cleaned)
    return sorted(tags)


def list_distinct_co_guides(db: Session) -> list[str]:
    rows = db.scalars(
        select(Project.co_guide).where(Project.co_guide.isnot(None), Project.co_guide != "")
    ).all()
    return sorted({strip_name_prefix(r) for r in rows if r})
