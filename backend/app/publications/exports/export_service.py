from __future__ import annotations

from collections import defaultdict
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.utils.pdf_tables import records_to_list_pdf_bytes
from app.publications.models import Faculty, Publication, PublicationFaculty

PUBLICATION_EXPORT_COLUMNS = [
    "title",
    "authors",
    "journal",
    "conference",
    "book",
    "volume",
    "issue",
    "pages",
    "publication_date",
    "publisher",
    "citation_count",
    "faculty_names",
]

PATENT_EXPORT_COLUMNS = [
    "title",
    "inventors",
    "patent_number",
    "patent_office",
    "application_number",
    "publication_date",
    "citation_count",
    "faculty_names",
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
    export_type: str = "both",
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
    if export_type == "publications":
        stmt = stmt.where(Publication.is_patent.is_(False))
    elif export_type == "patents":
        stmt = stmt.where(Publication.is_patent.is_(True))
    stmt = stmt.order_by(
        Publication.publication_year.is_(None).asc(),
        Publication.publication_year.desc(),
        Publication.id.desc(),
    )
    return list(db.scalars(stmt).all())


def _publication_record(row: Publication, faculty_names: str) -> dict:
    return {
        "title": row.title,
        "authors": row.authors,
        "journal": row.journal,
        "conference": row.conference,
        "book": row.book,
        "volume": row.volume,
        "issue": row.issue,
        "pages": row.pages,
        "publication_date": row.publication_date,
        "publisher": row.publisher,
        "citation_count": row.citation_count,
        "faculty_names": faculty_names,
    }


def _patent_record(row: Publication, faculty_names: str) -> dict:
    return {
        "title": row.title,
        "inventors": row.inventors,
        "patent_number": row.patent_number,
        "patent_office": row.patent_office,
        "application_number": row.application_number,
        "publication_date": row.publication_date,
        "citation_count": row.citation_count,
        "faculty_names": faculty_names,
    }


def _records_from_rows(
    db: Session,
    rows: list[Publication],
    export_type: str,
) -> tuple[list[dict], list[str]]:
    names_map = _faculty_names_map(db, [r.id for r in rows])
    publication_records: list[dict] = []
    patent_records: list[dict] = []
    for row in rows:
        faculty_names = names_map.get(row.id, "")
        if row.is_patent:
            if export_type in {"patents", "both"}:
                patent_records.append(_patent_record(row, faculty_names))
        elif export_type in {"publications", "both"}:
            publication_records.append(_publication_record(row, faculty_names))

    if export_type == "patents":
        return patent_records, PATENT_EXPORT_COLUMNS
    if export_type == "publications":
        return publication_records, PUBLICATION_EXPORT_COLUMNS

    combined = publication_records + patent_records
    columns = PUBLICATION_EXPORT_COLUMNS if publication_records else PATENT_EXPORT_COLUMNS
    if publication_records and patent_records:
        columns = list(dict.fromkeys(PUBLICATION_EXPORT_COLUMNS + PATENT_EXPORT_COLUMNS))
    return combined, columns


def _dataframe(records: list[dict], columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(records, columns=columns)


def export_publications_csv(
    db: Session,
    *,
    faculty_id: int | None = None,
    faculty_ids: list[int] | None = None,
    publication_year: int | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
    export_type: str = "both",
) -> bytes:
    rows = _query_publications(
        db,
        faculty_id=faculty_id,
        faculty_ids=faculty_ids,
        publication_year=publication_year,
        year_start=year_start,
        year_end=year_end,
        export_type=export_type,
    )
    records, columns = _records_from_rows(db, rows, export_type)
    return _dataframe(records, columns).to_csv(index=False).encode("utf-8")


def export_publications_excel(
    db: Session,
    *,
    faculty_id: int | None = None,
    faculty_ids: list[int] | None = None,
    publication_year: int | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
    scope: str = "all",
    export_type: str = "both",
) -> bytes:
    rows = _query_publications(
        db,
        faculty_id=faculty_id,
        faculty_ids=faculty_ids,
        publication_year=publication_year,
        year_start=year_start,
        year_end=year_end,
        export_type=export_type,
    )
    records, columns = _records_from_rows(db, rows, export_type)
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
                _dataframe(items, columns).to_excel(writer, index=False, sheet_name=safe)
        elif scope == "year":
            by_year: dict[str, list[dict]] = defaultdict(list)
            for rec in records:
                year_key = str(rec.get("publication_date") or rec.get("publication_year") or "Unknown")
                by_year[year_key].append(rec)
            for year_key, items in sorted(by_year.items(), reverse=True):
                _dataframe(items, columns).to_excel(writer, index=False, sheet_name=f"Year_{year_key}"[:31])
        elif export_type == "both":
            pub_rows = [r for r in rows if not r.is_patent]
            pat_rows = [r for r in rows if r.is_patent]
            pub_records, pub_cols = _records_from_rows(db, pub_rows, "publications")
            pat_records, pat_cols = _records_from_rows(db, pat_rows, "patents")
            if pub_records:
                _dataframe(pub_records, pub_cols).to_excel(writer, index=False, sheet_name="publications")
            if pat_records:
                _dataframe(pat_records, pat_cols).to_excel(writer, index=False, sheet_name="patents")
            if not pub_records and not pat_records:
                _dataframe([], columns).to_excel(writer, index=False, sheet_name="publications")
        else:
            _dataframe(records, columns).to_excel(writer, index=False, sheet_name=export_type)
    return output.getvalue()


def _pdf_records_publications(records: list[dict]) -> list[dict]:
    return [
        {
            "Title": rec.get("title") or "",
            "Authors": rec.get("authors") or "",
            "Journal": rec.get("journal") or "",
            "Conference": rec.get("conference") or "",
            "Book": rec.get("book") or "",
            "Volume": rec.get("volume") or "",
            "Issue": rec.get("issue") or "",
            "Pages": rec.get("pages") or "",
            "Date": rec.get("publication_date") or "",
            "Publisher": rec.get("publisher") or "",
            "Citations": str(rec.get("citation_count") or ""),
            "Faculty": rec.get("faculty_names") or "",
        }
        for rec in records
    ]


def _pdf_records_patents(records: list[dict]) -> list[dict]:
    return [
        {
            "Title": rec.get("title") or "",
            "Inventors": rec.get("inventors") or "",
            "Patent Number": rec.get("patent_number") or "",
            "Patent Office": rec.get("patent_office") or "",
            "Application Number": rec.get("application_number") or "",
            "Date": rec.get("publication_date") or "",
            "Citations": str(rec.get("citation_count") or ""),
            "Faculty": rec.get("faculty_names") or "",
        }
        for rec in records
    ]


def export_publications_pdf(
    db: Session,
    *,
    faculty_id: int | None = None,
    faculty_ids: list[int] | None = None,
    publication_year: int | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
    title: str = "Publications Export",
    export_type: str = "both",
) -> bytes:
    rows = _query_publications(
        db,
        faculty_id=faculty_id,
        faculty_ids=faculty_ids,
        publication_year=publication_year,
        year_start=year_start,
        year_end=year_end,
        export_type=export_type,
    )
    if export_type == "both":
        pub_records, _ = _records_from_rows(db, [r for r in rows if not r.is_patent], "publications")
        pat_records, _ = _records_from_rows(db, [r for r in rows if r.is_patent], "patents")
        pdf_records = _pdf_records_publications(pub_records) + _pdf_records_patents(pat_records)
    else:
        records, _ = _records_from_rows(db, rows, export_type)
        if export_type == "patents":
            pdf_records = _pdf_records_patents(records)
        else:
            pdf_records = _pdf_records_publications(records)
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
    export_type: str = "both",
) -> bytes:
    rows = _query_publications(
        db,
        faculty_ids=faculty_ids,
        publication_year=publication_year,
        year_start=year_start,
        year_end=year_end,
        export_type=export_type,
    )
    records, columns = _records_from_rows(db, rows, export_type)
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
            grouped[str(rec.get("publication_date") or "Unknown")].append(rec)
    else:
        raise ValueError(f"Unsupported grouping scope: {scope}")

    output = BytesIO()
    with ZipFile(output, mode="w", compression=ZIP_DEFLATED) as archive:
        for key, items in sorted(grouped.items()):
            safe_key = str(key).replace("/", "-").replace("\\", "-").strip() or "group"
            if format == "csv":
                payload = _dataframe(items, columns).to_csv(index=False).encode("utf-8")
                archive.writestr(f"publications_{scope}_{safe_key}.csv", payload)
            elif format == "pdf":
                if export_type == "patents":
                    pdf_records = _pdf_records_patents(items)
                else:
                    pdf_records = _pdf_records_publications(items)
                pdf = records_to_list_pdf_bytes(
                    f"Publications — {scope.title()}: {key}",
                    pdf_records,
                    entry_title_key="Title",
                )
                archive.writestr(f"publications_{scope}_{safe_key}.pdf", pdf)
            else:
                raise ValueError(f"Unsupported grouped archive format: {format}")
    return output.getvalue()
