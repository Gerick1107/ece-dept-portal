from __future__ import annotations

import io

import pandas as pd
from sqlalchemy.orm import Session

from app.course_allocation.services.allocation_service import list_allocations_view, list_courses_view


def export_allocations_xlsx(db: Session, **filters) -> bytes:
    view = list_allocations_view(db, **filters)
    rows: list[dict] = []
    for fr in view["faculty_rows"]:
        if fr["courses"]:
            for c in fr["courses"]:
                rows.append({**c, "faculty_name": fr["faculty_name"]})
        else:
            rows.append(
                {
                    "faculty_name": fr["faculty_name"],
                    "semester": filters.get("scope", ""),
                    "course_code": "NA",
                    "course_name": "NA",
                }
            )
    for u in view["unassigned"]:
        rows.append(u)
    cols = [
        "faculty_name",
        "semester",
        "academic_year",
        "course_code",
        "course_name",
        "ug_pg",
        "core_elective",
        "is_first_year",
    ]
    df = pd.DataFrame(rows)
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df = df[cols]
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()


def export_courses_xlsx(db: Session, **filters) -> bytes:
    view = list_courses_view(db, **filters)
    rows: list[dict] = []
    for cr in view["course_rows"]:
        if cr["allocations"]:
            for a in cr["allocations"]:
                rows.append({**a, "course_code": cr["course_code"], "course_name": cr["course_name"]})
        else:
            rows.append(
                {
                    "course_code": cr["course_code"],
                    "course_name": cr["course_name"],
                    "faculty_name": "NA",
                    "semester": filters.get("scope", ""),
                }
            )
    cols = [
        "course_code",
        "course_name",
        "faculty_name",
        "semester",
        "academic_year",
        "ug_pg",
        "core_elective",
        "is_first_year",
    ]
    df = pd.DataFrame(rows)
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df = df[cols]
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()
