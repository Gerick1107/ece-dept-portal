from __future__ import annotations

from io import BytesIO

import pandas as pd
from sqlalchemy.orm import Session

from app.fdps.services.fdp_service import list_fdps_filtered


def export_fdps_xlsx(
    db: Session,
    *,
    query: str | None = None,
    year: str | None = None,
    exact_year: int | None = None,
    exact_year_from: int | None = None,
    exact_year_to: int | None = None,
    year_from: str | None = None,
    year_to: str | None = None,
    faculty_names: list[str] | None = None,
    program_filter: str | None = None,
) -> bytes:
    rows = list_fdps_filtered(
        db,
        query=query,
        year=year,
        exact_year=exact_year,
        exact_year_from=exact_year_from,
        exact_year_to=exact_year_to,
        year_from=year_from,
        year_to=year_to,
        faculty_names=faculty_names,
        program_filter=program_filter,
    )
    frame = pd.DataFrame(
        [
            {
                "Faculty Name": r.faculty_name,
                "Academic Year": r.year,
                "Year": r.exact_year,
                "Program": r.program,
                "Description": r.description,
                "No. of Days": r.no_of_days,
                "No. of Attendees": r.no_of_attendees,
            }
            for r in rows
        ]
    )
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name="Faculty FDPs")
    return output.getvalue()
