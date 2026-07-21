from __future__ import annotations

from io import BytesIO

import pandas as pd
from sqlalchemy.orm import Session

from app.projects.services.project_service import ProjectSearchFilters, project_to_dict, search_projects
from app.projects.utils.course_name import normalize_course_name
from app.utils.pdf_tables import records_to_list_pdf_bytes

EXPORT_COLUMNS = [
    "Semester",
    "Title",
    "Course Code",
    "Course Name",
    "Guide",
    "Co-Guide",
    "Student Roll Number",
    "Student Name",
    "SDGs",
    "Credit",
]


def _rows_from_filters(db: Session, filters: ProjectSearchFilters) -> list[dict]:
    items, _ = search_projects(db, filters, page=1, page_size=10000)
    records = []
    for project in items:
        data = project_to_dict(db, project)
        confirmed = data["confirmed_sdgs"]
        suggested = data["suggested_sdgs"]
        sdg_parts = [f"SDG {s['sdg_number']} – {s['sdg_name']}" for s in confirmed]
        if not sdg_parts and suggested:
            sdg_parts = [
                f"SDG {s['sdg_number']} – {s['sdg_name']} (suggested)" for s in suggested
            ]
        sdg_text = "; ".join(sdg_parts)
        records.append(
            {
                "Semester": data["semesters"],
                "Title": data["project_title"],
                "Course Code": data["course_code"] or "",
                "Course Name": normalize_course_name(data["course_name"]) if data["course_name"] else "",
                "Guide": data["faculty_name"],
                "Co-Guide": data["co_guide"] or "",
                "Student Roll Number": data["student_roll_nos"],
                "Student Name": data["student_names"],
                "SDGs": sdg_text,
                "Credit": data["credit"] if data["credit"] is not None else "",
            }
        )
    return records


def export_projects_csv(db: Session, filters: ProjectSearchFilters) -> bytes:
    records = _rows_from_filters(db, filters)
    frame = pd.DataFrame(records, columns=EXPORT_COLUMNS)
    return frame.to_csv(index=False).encode("utf-8")


def export_projects_excel(db: Session, filters: ProjectSearchFilters) -> bytes:
    records = _rows_from_filters(db, filters)
    frame = pd.DataFrame(records, columns=EXPORT_COLUMNS)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name="projects")
    return output.getvalue()


def export_projects_pdf(db: Session, filters: ProjectSearchFilters, title: str = "Projects and Theses") -> bytes:
    records = _rows_from_filters(db, filters)
    pdf_records = [
        {
            "Title": str(row["Title"]),
            "Semester": str(row["Semester"]),
            "Course Code": str(row["Course Code"]),
            "Guide": str(row["Guide"]),
            "Students": str(row["Student Name"]),
            "SDGs": str(row["SDGs"]),
            "Credit": str(row["Credit"]),
        }
        for row in records
    ]
    return records_to_list_pdf_bytes(title, pdf_records, entry_title_key="Title")
