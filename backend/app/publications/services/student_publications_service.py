from __future__ import annotations

import json
import re
from io import BytesIO
from typing import Any

import pandas as pd
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.publications.models.student_publication import StudentPublication

CORE_HEADERS = ("Title", "Authors", "Years")

_TITLE_ALIASES = {"title", "paper title", "publication title"}
_AUTHOR_ALIASES = {"authors", "author", "author names"}
_YEAR_ALIASES = {"years", "year", "publication year", "pub year"}


def _norm_header(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).strip()


def _header_key(value: Any) -> str:
    return _norm_header(value).lower()


def get_extra_fields(row: StudentPublication) -> dict[str, str]:
    if not row.extra_fields:
        return {}
    try:
        data = json.loads(row.extra_fields)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): "" if v is None else str(v) for k, v in data.items()}


def set_extra_fields(row: StudentPublication, values: dict[str, Any] | None) -> None:
    cleaned = {str(k): "" if v is None else str(v) for k, v in (values or {}).items() if str(k).strip()}
    row.extra_fields = json.dumps(cleaned, ensure_ascii=False) if cleaned else None


def row_to_dict(row: StudentPublication) -> dict[str, Any]:
    extras = get_extra_fields(row)
    return {
        "id": row.id,
        "title": row.title,
        "authors": row.authors,
        "publication_year": row.publication_year,
        "extra_fields": extras,
        "fields": {
            "Title": row.title,
            "Authors": row.authors or "",
            "Years": "" if row.publication_year is None else str(row.publication_year),
            **extras,
        },
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def collect_columns(db: Session) -> list[str]:
    columns = list(CORE_HEADERS)
    seen = {c.lower() for c in columns}
    rows = db.scalars(select(StudentPublication.extra_fields)).all()
    for raw in rows:
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        for key in data.keys():
            label = str(key)
            if label.lower() in seen:
                continue
            seen.add(label.lower())
            columns.append(label)
    return columns


def list_student_publications(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    title_query: str | None = None,
    authors_query: str | None = None,
    year: int | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    sort_dir: str = "desc",
) -> tuple[list[StudentPublication], int, list[str]]:
    stmt = select(StudentPublication)
    if title_query:
        stmt = stmt.where(StudentPublication.title.ilike(f"%{title_query.strip()}%"))
    if authors_query:
        stmt = stmt.where(StudentPublication.authors.ilike(f"%{authors_query.strip()}%"))
    if year is not None:
        stmt = stmt.where(StudentPublication.publication_year == year)
    if year_min is not None:
        stmt = stmt.where(StudentPublication.publication_year >= year_min)
    if year_max is not None:
        stmt = stmt.where(StudentPublication.publication_year <= year_max)

    if (sort_dir or "desc").lower() == "asc":
        stmt = stmt.order_by(
            StudentPublication.publication_year.is_(None).asc(),
            StudentPublication.publication_year.asc(),
            StudentPublication.id.asc(),
        )
    else:
        stmt = stmt.order_by(
            StudentPublication.publication_year.is_(None).asc(),
            StudentPublication.publication_year.desc(),
            StudentPublication.id.desc(),
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all())
    return items, int(total), collect_columns(db)


def create_student_publication(
    db: Session,
    *,
    title: str,
    authors: str | None = None,
    publication_year: int | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> StudentPublication:
    title_clean = (title or "").strip()
    if not title_clean:
        raise ValueError("Title is required")
    row = StudentPublication(
        title=title_clean,
        authors=(authors or "").strip() or None,
        publication_year=publication_year,
    )
    set_extra_fields(row, extra_fields)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_student_publication(db: Session, publication_id: int) -> bool:
    row = db.get(StudentPublication, publication_id)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def _parse_year(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "-"}:
        return None
    match = re.search(r"(19|20)\d{2}", text)
    if not match:
        return None
    try:
        return int(match.group(0))
    except ValueError:
        return None


def _classify_headers(headers: list[str]) -> tuple[str | None, str | None, str | None, list[str]]:
    title_col = authors_col = year_col = None
    extras: list[str] = []
    for header in headers:
        key = _header_key(header)
        if title_col is None and key in _TITLE_ALIASES:
            title_col = header
        elif authors_col is None and key in _AUTHOR_ALIASES:
            authors_col = header
        elif year_col is None and key in _YEAR_ALIASES:
            year_col = header
        else:
            extras.append(header)
    return title_col, authors_col, year_col, extras


def import_student_publications_excel(db: Session, content: bytes, filename: str = "") -> dict[str, Any]:
    lower = (filename or "").lower()
    engine = "xlrd" if lower.endswith(".xls") and not lower.endswith(".xlsx") else "openpyxl"
    try:
        frame = pd.read_excel(BytesIO(content), engine=engine, dtype=object)
    except Exception:
        alternate = "openpyxl" if engine == "xlrd" else "xlrd"
        frame = pd.read_excel(BytesIO(content), engine=alternate, dtype=object)

    if frame.empty:
        raise ValueError("Excel file has no data rows")

    frame.columns = [_norm_header(c) for c in frame.columns]
    title_col, authors_col, year_col, extra_cols = _classify_headers(list(frame.columns))
    if not title_col:
        raise ValueError("Excel must include a Title column")
    if not authors_col:
        raise ValueError("Excel must include an Authors column")
    if not year_col:
        raise ValueError("Excel must include a Years/Year column")

    inserted = 0
    skipped = 0
    errors: list[str] = []
    for idx, series in frame.iterrows():
        try:
            title = str(series.get(title_col) or "").strip()
            if not title or title.lower() == "nan":
                skipped += 1
                continue
            authors_raw = series.get(authors_col)
            authors = None if authors_raw is None or str(authors_raw).strip().lower() in {"", "nan"} else str(authors_raw).strip()
            year = _parse_year(series.get(year_col))
            extras: dict[str, str] = {}
            for col in extra_cols:
                raw = series.get(col)
                if raw is None or str(raw).strip().lower() in {"", "nan"}:
                    continue
                extras[col] = str(raw).strip()
            create_student_publication(
                db,
                title=title,
                authors=authors,
                publication_year=year,
                extra_fields=extras,
            )
            inserted += 1
        except Exception as exc:
            skipped += 1
            errors.append(f"Row {int(idx) + 2}: {exc}")

    return {
        "inserted": inserted,
        "skipped": skipped,
        "columns": collect_columns(db),
        "errors": errors[:50],
    }


def build_student_publications_template() -> bytes:
    frame = pd.DataFrame(columns=list(CORE_HEADERS))
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name="Student Publications")
    return output.getvalue()
