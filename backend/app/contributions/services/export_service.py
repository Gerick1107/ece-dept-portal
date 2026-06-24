from __future__ import annotations

import io

import pandas as pd
from sqlalchemy.orm import Session

from app.contributions.services.contribution_service import list_contributions

EXPORT_COLUMNS: dict[str, list[str]] = {
    "memberships": ["faculty_name", "society_name", "grade_position"],
    "resource-person-events": [
        "faculty_name",
        "year",
        "exact_year",
        "program_name",
        "event_date",
        "location",
        "organized_by",
    ],
    "mooc-development": ["faculty_name", "course_name", "platform", "remarks"],
    "department-fdp-events": [
        "faculty_name",
        "year",
        "exact_year",
        "program_name",
        "event_date",
        "duration",
        "speaker_affiliation",
        "co_speakers",
        "no_of_attendees",
    ],
    "student-project-support": [
        "faculty_name",
        "year",
        "exact_year",
        "event_name",
        "event_date",
        "place",
        "website_link",
    ],
    "collaborations": [
        "faculty_name",
        "collaboration_type",
        "company_place",
        "duration",
        "outcomes",
    ],
    "faculty-services": [
        "faculty_name",
        "year",
        "exact_year",
        "scope",
        "role_title",
        "organization",
        "start_date",
        "end_date",
        "duration_text",
        "description",
    ],
    "phd-students": [
        "faculty_name",
        "as_of_year",
        "students_graduated",
        "ongoing_phd_students",
    ],
}


def export_contributions_xlsx(
    db: Session,
    resource: str,
    *,
    query: str | None = None,
    year: str | None = None,
    exact_year: int | None = None,
    exact_year_from: int | None = None,
    exact_year_to: int | None = None,
    year_from: str | None = None,
    year_to: str | None = None,
    faculty_id: int | None = None,
    extra_filter: str | None = None,
) -> bytes:
    rows = list_contributions(
        db,
        resource,
        query=query,
        year=year,
        exact_year=exact_year,
        faculty_id=faculty_id,
        extra_filter=extra_filter,
    )
    if exact_year_from is not None:
        rows = [
            r
            for r in rows
            if (getattr(r, "as_of_year", None) if resource == "phd-students" else getattr(r, "exact_year", None))
            is not None
            and (getattr(r, "as_of_year", None) if resource == "phd-students" else getattr(r, "exact_year", None))
            >= exact_year_from
        ]
    if exact_year_to is not None:
        rows = [
            r
            for r in rows
            if (getattr(r, "as_of_year", None) if resource == "phd-students" else getattr(r, "exact_year", None))
            is not None
            and (getattr(r, "as_of_year", None) if resource == "phd-students" else getattr(r, "exact_year", None))
            <= exact_year_to
        ]
    if year_from and hasattr(rows[0] if rows else None, "year"):
        rows = [r for r in rows if getattr(r, "year", None) and r.year >= year_from.strip()]
    if year_to and rows and hasattr(rows[0], "year"):
        rows = [r for r in rows if getattr(r, "year", None) and r.year <= year_to.strip()]

    cols = EXPORT_COLUMNS[resource]
    data = [{c: getattr(r, c, None) for c in cols} for r in rows]
    df = pd.DataFrame(data, columns=cols)
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()
