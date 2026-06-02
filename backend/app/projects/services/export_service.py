from __future__ import annotations

from io import BytesIO

import pandas as pd
from sqlalchemy.orm import Session

from app.projects.services.project_service import ProjectSearchFilters, project_to_dict, search_projects
from app.utils.pdf_tables import records_to_list_pdf_bytes

EXPORT_COLUMNS = [
    "sl_no",
    "semester",
    "project_topic",
    "project_type",
    "faculty",
    "co_guide",
    "students",
    "sdgs",
    "status",
    "credit",
]


def _rows_from_filters(db: Session, filters: ProjectSearchFilters) -> list[dict]:
    items, _ = search_projects(db, filters, page=1, page_size=10000)
    records = []
    for i, project in enumerate(items, start=1):
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
                "sl_no": i,
                "semester": data["semester"],
                "project_topic": data["project_title"],
                "project_type": data["project_type"],
                "faculty": data["faculty_name"],
                "co_guide": data["co_guide"] or "",
                "students": "; ".join(data["students"]),
                "sdgs": sdg_text,
                "status": data["status"],
                "credit": data["credit"] or "",
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


def export_projects_pdf(db: Session, filters: ProjectSearchFilters, title: str = "BTP/IP Projects") -> bytes:
    records = _rows_from_filters(db, filters)
    pdf_records = [
        {
            "Project Topic": str(row["project_topic"]),
            "Semester": str(row["semester"]),
            "Project Type": str(row["project_type"]),
            "Faculty": str(row["faculty"]),
            "Co Guide": str(row["co_guide"]),
            "Students": str(row["students"]),
            "SDGs": str(row["sdgs"]),
            "Status": str(row["status"]),
            "Credit": str(row["credit"]),
        }
        for row in records
    ]
    return records_to_list_pdf_bytes(title, pdf_records, entry_title_key="Project Topic")
