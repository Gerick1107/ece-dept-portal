from __future__ import annotations

from collections import defaultdict
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.utils.pdf_tables import records_to_list_pdf_bytes
from app.publications.models import Faculty, Publication, PublicationFaculty

EXPORT_COLUMNS = [
    "id",
    "title",
    "authors",
    "publication_year",
    "faculty_names",
    "journal_or_conference",
    "publisher",
    "citation_count",
    "publication_type",
]


def _faculty_names_map(db: Session, publication_ids: list[int]) -> dict[int, str]:
    if not publication_ids:
        return {}
    rows = db.execute(
        select(PublicationFaculty.publication_id, Faculty.name)
        .join(Faculty, Faculty.id == PublicationFaculty.faculty_id)
        .where(PublicationFaculty.publication_id.in_(publication_ids))
    ).all()
    grouped: dict[int, list[str]] = defaultdict(list)
    for pub_id, name in rows:
        grouped[pub_id].append(name)
    return {pid: "; ".join(names) for pid, names in grouped.items()}


def _query_publications(
    db: Session,
    *,
    faculty_id: int | None = None,
    faculty_ids: list[int] | None = None,
    publication_year: int | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
) -> list[Publication]:
    stmt = select(Publication)
    resolved_faculty_ids: list[int] = []
    if faculty_ids:
        resolved_faculty_ids.extend(faculty_ids)
    if faculty_id is not None:
        resolved_faculty_ids.append(faculty_id)
    resolved_faculty_ids = sorted(set(resolved_faculty_ids))
    if resolved_faculty_ids:
        stmt = stmt.where(
            Publication.id.in_(
                select(PublicationFaculty.publication_id).where(
                    PublicationFaculty.faculty_id.in_(resolved_faculty_ids)
                )
            )
        )
    if publication_year is not None:
        stmt = stmt.where(Publication.publication_year == publication_year)
    if year_start is not None:
        stmt = stmt.where(Publication.publication_year >= year_start)
    if year_end is not None:
        stmt = stmt.where(Publication.publication_year <= year_end)
    stmt = stmt.order_by(
        Publication.publication_year.is_(None).asc(),
        Publication.publication_year.desc(),
        Publication.id.desc(),
    )
    return list(db.scalars(stmt).all())


def _records_from_rows(db: Session, rows: list[Publication]) -> list[dict]:
    names_map = _faculty_names_map(db, [r.id for r in rows])
    return [
        {
            "id": row.id,
            "title": row.title,
            "authors": row.authors,
            "publication_year": row.publication_year,
            "faculty_names": names_map.get(row.id, ""),
            "journal_or_conference": row.journal_or_conference,
            "publisher": row.publisher,
            "citation_count": row.citation_count,
            "publication_type": row.publication_type,
        }
        for row in rows
    ]


def _dataframe(records: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(records, columns=EXPORT_COLUMNS)


def export_publications_csv(
    db: Session,
    *,
    faculty_id: int | None = None,
    faculty_ids: list[int] | None = None,
    publication_year: int | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
) -> bytes:
    rows = _query_publications(
        db,
        faculty_id=faculty_id,
        faculty_ids=faculty_ids,
        publication_year=publication_year,
        year_start=year_start,
        year_end=year_end,
    )
    frame = _dataframe(_records_from_rows(db, rows))
    return frame.to_csv(index=False).encode("utf-8")


def export_publications_excel(
    db: Session,
    *,
    faculty_id: int | None = None,
    faculty_ids: list[int] | None = None,
    publication_year: int | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
    scope: str = "all",
) -> bytes:
    rows = _query_publications(
        db,
        faculty_id=faculty_id,
        faculty_ids=faculty_ids,
        publication_year=publication_year,
        year_start=year_start,
        year_end=year_end,
    )
    records = _records_from_rows(db, rows)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        if scope == "faculty" and faculty_id is None:
            by_faculty: dict[str, list[dict]] = defaultdict(list)
            for rec in records:
                key = rec.get("faculty_names") or "Unassigned"
                for part in key.split(";"):
                    name = part.strip()
                    if name:
                        by_faculty[name].append(rec)
            for sheet_name, items in by_faculty.items():
                safe = sheet_name[:31].replace("/", "-") or "Faculty"
                _dataframe(items).to_excel(writer, index=False, sheet_name=safe)
        elif scope == "year":
            by_year: dict[str, list[dict]] = defaultdict(list)
            for rec in records:
                year_key = str(rec.get("publication_year") or "Unknown")
                by_year[year_key].append(rec)
            for year_key, items in sorted(by_year.items(), reverse=True):
                _dataframe(items).to_excel(writer, index=False, sheet_name=f"Year_{year_key}"[:31])
        else:
            _dataframe(records).to_excel(writer, index=False, sheet_name="publications")
    return output.getvalue()


def export_publications_pdf(
    db: Session,
    *,
    faculty_id: int | None = None,
    faculty_ids: list[int] | None = None,
    publication_year: int | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
    title: str = "Publications Export",
) -> bytes:
    rows = _query_publications(
        db,
        faculty_id=faculty_id,
        faculty_ids=faculty_ids,
        publication_year=publication_year,
        year_start=year_start,
        year_end=year_end,
    )
    records = _records_from_rows(db, rows)
    pdf_records = [
        {
            "Title": rec.get("title") or "",
            "Authors": rec.get("authors") or "",
            "Year": str(rec.get("publication_year") or ""),
            "Faculty": rec.get("faculty_names") or "",
            "Journal or Conference": rec.get("journal_or_conference") or "",
            "Publisher": rec.get("publisher") or "",
            "Citations": str(rec.get("citation_count") or ""),
            "Type": rec.get("publication_type") or "",
        }
        for rec in records
    ]
    return records_to_list_pdf_bytes(title, pdf_records, entry_title_key="Title")


def export_publications_grouped_archive(
    db: Session,
    *,
    format: str,
    scope: str,
    faculty_ids: list[int] | None = None,
    publication_year: int | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
) -> bytes:
    rows = _query_publications(
        db,
        faculty_ids=faculty_ids,
        publication_year=publication_year,
        year_start=year_start,
        year_end=year_end,
    )
    records = _records_from_rows(db, rows)
    if scope == "faculty":
        grouped: dict[str, list[dict]] = defaultdict(list)
        for rec in records:
            names = rec.get("faculty_names") or "Unassigned"
            for part in names.split(";"):
                name = part.strip() or "Unassigned"
                grouped[name].append(rec)
    elif scope == "year":
        grouped = defaultdict(list)
        for rec in records:
            grouped[str(rec.get("publication_year") or "Unknown")].append(rec)
    else:
        raise ValueError(f"Unsupported grouping scope: {scope}")

    output = BytesIO()
    with ZipFile(output, mode="w", compression=ZIP_DEFLATED) as archive:
        for key, items in sorted(grouped.items()):
            safe_key = str(key).replace("/", "-").replace("\\", "-").strip() or "group"
            if format == "csv":
                payload = _dataframe(items).to_csv(index=False).encode("utf-8")
                archive.writestr(f"publications_{scope}_{safe_key}.csv", payload)
            elif format == "pdf":
                pdf_records = [
                    {
                        "Title": rec.get("title") or "",
                        "Authors": rec.get("authors") or "",
                        "Year": str(rec.get("publication_year") or ""),
                        "Faculty": rec.get("faculty_names") or "",
                        "Journal or Conference": rec.get("journal_or_conference") or "",
                        "Publisher": rec.get("publisher") or "",
                        "Citations": str(rec.get("citation_count") or ""),
                        "Type": rec.get("publication_type") or "",
                    }
                    for rec in items
                ]
                pdf = records_to_list_pdf_bytes(
                    f"Publications — {scope.title()}: {key}",
                    pdf_records,
                    entry_title_key="Title",
                )
                archive.writestr(f"publications_{scope}_{safe_key}.pdf", pdf)
            else:
                raise ValueError(f"Unsupported grouped archive format: {format}")
    return output.getvalue()
