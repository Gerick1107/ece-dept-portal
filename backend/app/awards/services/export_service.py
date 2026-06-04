from __future__ import annotations

from io import BytesIO

import pandas as pd
from sqlalchemy.orm import Session

from app.awards.services.award_service import list_awards_filtered


def export_awards_xlsx(
    db: Session,
    *,
    query: str | None = None,
    year: str | None = None,
    year_from: str | None = None,
    year_to: str | None = None,
    faculty_names: list[str] | None = None,
) -> bytes:
    rows = list_awards_filtered(
        db,
        query=query,
        year=year,
        year_from=year_from,
        year_to=year_to,
        faculty_names=faculty_names,
    )
    frame = pd.DataFrame(
        [
            {
                "Faculty Name": r.faculty_name,
                "Year": r.year,
                "Award / Recognition": r.award,
            }
            for r in rows
        ]
    )
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name="Faculty Awards")
    return output.getvalue()
