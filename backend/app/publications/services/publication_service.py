from __future__ import annotations

import json

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.publications.models import (
    BlockedPublication,
    Faculty,
    Publication,
    PublicationAuditLog,
    PublicationFaculty,
)
from app.publications.schemas import (
    FacultyCreate,
    FacultyUpdate,
    PublicationCreate,
    PublicationUpdate,
)
from app.publications.utils.helpers import make_source_hash
from app.publications.utils.link_filters import (
    article_has_blocked_repository_link,
    has_blocked_repository_link,
    publication_has_blocked_repository_link,
)

# Fields faculty/admin may edit in the portal. Everything else stays scrape-owned.
EDITABLE_PUBLICATION_FIELDS = frozenset(
    {
        "publisher",
        "publication_date",
        "pages",
        "conference",
        "journal",
        "book",
        "volume",
        "issue",
        "patent_office",
        "patent_number",
        "application_number",
        "is_manual_book",
        "custom_fields",
    }
)

# Scrape / identity fields that must never be overwritten by UI edits.
LOCKED_PUBLICATION_FIELDS = frozenset(
    {
        "title",
        "authors",
        "inventors",
        "publication_year",
        "citation_count",
        "is_patent",
        "scholar_url",
        "source_hash",
        "raw_metadata",
        "is_iiitd_publication",
        "link",
        "pdf_url",
        "created_at",
        "updated_at",
        "id",
    }
)


def get_manual_overrides(publication: Publication) -> list[str]:
    raw = publication.manual_overrides
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [str(item) for item in data if isinstance(item, str)]


def set_manual_overrides(publication: Publication, fields: list[str]) -> None:
    cleaned = sorted({f for f in fields if f in EDITABLE_PUBLICATION_FIELDS})
    publication.manual_overrides = json.dumps(cleaned) if cleaned else None


def apply_updates_respecting_overrides(
    publication: Publication,
    updates: dict,
    *,
    force: bool = False,
) -> list[str]:
    """Apply scraped/enriched values, skipping any manually overridden fields."""
    overrides = set(get_manual_overrides(publication))
    applied: list[str] = []
    for key, value in updates.items():
        if not hasattr(publication, key):
            continue
        if not force and key in overrides:
            continue
        setattr(publication, key, value)
        applied.append(key)
    return applied


def _faculty_query(search: str | None, department: str | None, include_inactive: bool) -> Select[tuple[Faculty]]:
    stmt = select(Faculty)
    if search:
        stmt = stmt.where(Faculty.name.ilike(f"%{search.strip()}%"))
    if department:
        stmt = stmt.where(Faculty.department == department.strip())
    if not include_inactive:
        stmt = stmt.where(Faculty.is_active.is_(True))
    return stmt


def list_faculty(
    db: Session,
    page: int,
    page_size: int,
    search: str | None = None,
    department: str | None = None,
    include_inactive: bool = False,
) -> tuple[list[tuple[Faculty, int]], int]:
    filtered = _faculty_query(search, department, include_inactive).subquery()
    stmt = (
        select(Faculty, func.count(PublicationFaculty.id))
        .join(filtered, Faculty.id == filtered.c.id)
        .outerjoin(PublicationFaculty, PublicationFaculty.faculty_id == Faculty.id)
        .group_by(Faculty.id)
        .order_by(Faculty.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    total = db.scalar(select(func.count()).select_from(filtered)) or 0
    rows = db.execute(stmt).all()
    return rows, int(total)


def create_faculty(db: Session, body: FacultyCreate) -> Faculty:
    from app.publications.services.faculty_master_csv import upsert_faculty_master_csv_row
    from app.publications.utils.helpers import normalize_scholar_id

    payload = body.model_dump()
    payload["scholar_id"] = normalize_scholar_id(payload.get("scholar_id") or "")
    if not payload["scholar_id"]:
        raise ValueError("scholar_id is required")
    obj = Faculty(**payload, is_active=body.leave_year is None)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    try:
        upsert_faculty_master_csv_row(obj)
    except Exception:
        # DB is source of truth; CSV write failures should not roll back the create.
        pass
    return obj


def update_faculty(db: Session, faculty: Faculty, body: FacultyUpdate) -> Faculty:
    from app.publications.services.faculty_master_csv import upsert_faculty_master_csv_row

    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(faculty, key, value)
    if "leave_year" in data and "is_active" not in data:
        faculty.is_active = faculty.leave_year is None
    db.commit()
    db.refresh(faculty)
    try:
        upsert_faculty_master_csv_row(faculty)
    except Exception:
        pass
    return faculty


def list_publications(
    db: Session,
    page: int,
    page_size: int,
    query: str | None = None,
    faculty_id: int | None = None,
    publication_year: int | None = None,
    is_patent: bool | None = None,
    search_by: str = "title",
    category: str | None = None,
) -> tuple[list[Publication], int]:
    stmt = select(Publication)
    # Hard exclude repository.iiitd.edu.in even if a prior purge missed a row.
    # Use COALESCE so NULL link columns are not dropped by SQL three-valued logic.
    repo_pat = "%repository.iiitd.edu.in%"
    stmt = stmt.where(
        ~func.lower(func.coalesce(Publication.link, "")).like(repo_pat),
        ~func.lower(func.coalesce(Publication.scholar_url, "")).like(repo_pat),
        ~func.lower(func.coalesce(Publication.pdf_url, "")).like(repo_pat),
        ~func.lower(func.coalesce(Publication.raw_metadata, "")).like(repo_pat),
    )
    if query:
        pattern = f"%{query.strip()}%"
        search_by_norm = (search_by or "title").strip().lower()
        if search_by_norm == "venue":
            stmt = stmt.where(
                or_(
                    Publication.journal.ilike(pattern),
                    Publication.conference.ilike(pattern),
                    Publication.book.ilike(pattern),
                    Publication.publisher.ilike(pattern),
                )
            )
        else:
            stmt = stmt.where(Publication.title.ilike(pattern))
    if publication_year is not None:
        stmt = stmt.where(Publication.publication_year == publication_year)
    if is_patent is not None:
        stmt = stmt.where(Publication.is_patent.is_(is_patent))
    if faculty_id is not None:
        stmt = stmt.join(PublicationFaculty, PublicationFaculty.publication_id == Publication.id).where(
            PublicationFaculty.faculty_id == faculty_id
        )
    if category == "journals":
        stmt = stmt.where(Publication.is_patent.is_(False), Publication.journal.isnot(None), Publication.journal != "")
    elif category == "conferences":
        stmt = stmt.where(
            Publication.is_patent.is_(False),
            Publication.conference.isnot(None),
            Publication.conference != "",
        )
    elif category == "book_chapters":
        stmt = stmt.where(Publication.is_patent.is_(False), Publication.book.isnot(None), Publication.book != "")
    elif category == "books":
        stmt = stmt.where(Publication.is_patent.is_(False), Publication.is_manual_book.is_(True))
    elif category == "preprints":
        # arXiv-like venues or completely empty venue columns.
        empty_journal = or_(Publication.journal.is_(None), Publication.journal == "")
        empty_conference = or_(Publication.conference.is_(None), Publication.conference == "")
        empty_book = or_(Publication.book.is_(None), Publication.book == "")
        stmt = stmt.where(
            Publication.is_patent.is_(False),
            or_(
                Publication.journal.ilike("%arxiv%"),
                Publication.conference.ilike("%arxiv%"),
                Publication.book.ilike("%arxiv%"),
                (empty_journal & empty_conference & empty_book),
            ),
        )

    stmt = stmt.order_by(
        Publication.publication_year.is_(None).asc(),
        Publication.publication_year.desc(),
        Publication.id.desc(),
    )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return items, int(total)


def _sync_publication_faculty(db: Session, publication: Publication, faculty_ids: list[int]) -> None:
    db.query(PublicationFaculty).filter(PublicationFaculty.publication_id == publication.id).delete()
    for fid in sorted(set(faculty_ids)):
        db.add(PublicationFaculty(publication_id=publication.id, faculty_id=fid))


def create_publication(db: Session, body: PublicationCreate) -> Publication:
    if has_blocked_repository_link(body.link, body.scholar_url, body.pdf_url):
        raise ValueError("Publications linking to repository.iiitd.edu.in are not allowed")

    source_hash = make_source_hash(body.title, body.publication_year)
    blocked = db.scalar(select(BlockedPublication).where(BlockedPublication.source_hash == source_hash))
    if blocked:
        raise ValueError("Publication is blocked due to a prior manual deletion")

    existing = db.scalar(select(Publication).where(Publication.source_hash == source_hash))
    if existing:
        raise ValueError("Publication already exists")

    obj = Publication(source_hash=source_hash, **body.model_dump(exclude={"faculty_ids"}))
    db.add(obj)
    db.flush()
    _sync_publication_faculty(db, obj, body.faculty_ids)
    db.add(
        PublicationAuditLog(
            action="manual_create",
            publication_id=obj.id,
            source_hash=obj.source_hash,
            details=f"faculty_ids={body.faculty_ids}",
        )
    )
    db.commit()
    db.refresh(obj)
    return obj


def update_publication(db: Session, publication: Publication, body: PublicationUpdate) -> Publication:
    from app.publications.services.custom_columns_service import get_custom_fields, set_custom_fields

    data = body.model_dump(exclude_unset=True)
    custom_fields = data.pop("custom_fields", None)
    overrides = set(get_manual_overrides(publication))

    for key, value in data.items():
        if key not in EDITABLE_PUBLICATION_FIELDS or key == "custom_fields":
            continue
        setattr(publication, key, value)
        overrides.add(key)

    if custom_fields is not None:
        existing = get_custom_fields(publication)
        existing.update({str(k): str(v) for k, v in custom_fields.items() if v is not None})
        set_custom_fields(publication, existing)
        overrides.add("custom_fields")

    set_manual_overrides(publication, sorted(overrides))
    db.add(
        PublicationAuditLog(
            action="manual_update",
            publication_id=publication.id,
            source_hash=publication.source_hash,
            details=f"updated_fields={sorted(data.keys())}",
        )
    )
    db.commit()
    db.refresh(publication)
    return publication


def delete_publications(
    db: Session,
    publication_ids: list[int],
    *,
    reason: str = "manual_deletion",
) -> tuple[int, int]:
    if not publication_ids:
        return 0, 0

    rows = db.scalars(select(Publication).where(Publication.id.in_(publication_ids))).all()
    if not rows:
        return 0, 0

    db.query(PublicationFaculty).filter(PublicationFaculty.publication_id.in_(publication_ids)).delete(
        synchronize_session=False
    )
    blocked_added = 0
    for row in rows:
        exists = db.scalar(select(BlockedPublication).where(BlockedPublication.source_hash == row.source_hash))
        if not exists:
            db.add(
                BlockedPublication(
                    source_hash=row.source_hash,
                    title=row.title,
                    reason=reason,
                )
            )
            blocked_added += 1
        db.add(
            PublicationAuditLog(
                action="manual_delete",
                publication_id=row.id,
                source_hash=row.source_hash,
                details=row.title,
            )
        )
    deleted = db.query(Publication).filter(Publication.id.in_(publication_ids)).delete()
    db.commit()
    return int(deleted), blocked_added


def purge_repository_publications(db: Session) -> int:
    """Delete any publications whose links point at repository.iiitd.edu.in and tombstone them."""
    rows = list(db.scalars(select(Publication)).all())
    victim_ids = [row.id for row in rows if publication_has_blocked_repository_link(row)]
    if not victim_ids:
        return 0
    deleted, _ = delete_publications(db, victim_ids, reason="blocked_repository_iiitd")
    return deleted


def should_skip_scraped_article(db: Session, article: dict, *, title: str, year: int | None) -> bool:
    if article_has_blocked_repository_link(article):
        return True
    source_hash = make_source_hash(title, year)
    blocked = db.scalar(select(BlockedPublication).where(BlockedPublication.source_hash == source_hash))
    return blocked is not None


def publication_faculty_ids(db: Session, publication_id: int) -> list[int]:
    return list(
        db.scalars(
            select(PublicationFaculty.faculty_id).where(PublicationFaculty.publication_id == publication_id)
        ).all()
    )


def publication_faculty_ids_map(db: Session, publication_ids: list[int]) -> dict[int, list[int]]:
    if not publication_ids:
        return {}
    rows = db.execute(
        select(PublicationFaculty.publication_id, PublicationFaculty.faculty_id).where(
            PublicationFaculty.publication_id.in_(publication_ids)
        )
    ).all()
    mapping: dict[int, list[int]] = {}
    for publication_id, faculty_id in rows:
        mapping.setdefault(publication_id, []).append(faculty_id)
    return mapping


def user_can_manage_publication(db: Session, *, publication_id: int, faculty_id: int | None, see_all: bool) -> bool:
    if see_all:
        return True
    if faculty_id is None:
        return False
    ids = publication_faculty_ids(db, publication_id)
    return faculty_id in ids
