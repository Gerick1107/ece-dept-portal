from __future__ import annotations

from sqlalchemy import Select, func, select
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
    obj = Faculty(**body.model_dump(), is_active=body.leave_year is None)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_faculty(db: Session, faculty: Faculty, body: FacultyUpdate) -> Faculty:
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(faculty, key, value)
    if "leave_year" in data and "is_active" not in data:
        faculty.is_active = faculty.leave_year is None
    db.commit()
    db.refresh(faculty)
    return faculty


def list_publications(
    db: Session,
    page: int,
    page_size: int,
    query: str | None = None,
    faculty_id: int | None = None,
    publication_year: int | None = None,
    is_patent: bool | None = None,
) -> tuple[list[Publication], int]:
    stmt = select(Publication)
    if query:
        pattern = f"%{query.strip()}%"
        stmt = stmt.where(Publication.title.ilike(pattern))
    if publication_year is not None:
        stmt = stmt.where(Publication.publication_year == publication_year)
    if is_patent is not None:
        stmt = stmt.where(Publication.is_patent.is_(is_patent))
    if faculty_id is not None:
        stmt = stmt.join(PublicationFaculty, PublicationFaculty.publication_id == Publication.id).where(
            PublicationFaculty.faculty_id == faculty_id
        )

    stmt = stmt.order_by(Publication.publication_year.is_(None).asc(), Publication.publication_year.desc(), Publication.id.desc())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return items, int(total)


def _sync_publication_faculty(db: Session, publication: Publication, faculty_ids: list[int]) -> None:
    db.query(PublicationFaculty).filter(PublicationFaculty.publication_id == publication.id).delete()
    for fid in sorted(set(faculty_ids)):
        db.add(PublicationFaculty(publication_id=publication.id, faculty_id=fid))


def create_publication(db: Session, body: PublicationCreate) -> Publication:
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
    data = body.model_dump(exclude_unset=True)
    faculty_ids = data.pop("faculty_ids", None)
    for key, value in data.items():
        setattr(publication, key, value)

    if "title" in data or "publication_year" in data:
        publication.source_hash = make_source_hash(publication.title, publication.publication_year)
    if faculty_ids is not None:
        _sync_publication_faculty(db, publication, faculty_ids)
    db.add(
        PublicationAuditLog(
            action="manual_update",
            publication_id=publication.id,
            source_hash=publication.source_hash,
            details=f"updated_fields={list(data.keys())}",
        )
    )
    db.commit()
    db.refresh(publication)
    return publication


def delete_publications(db: Session, publication_ids: list[int]) -> tuple[int, int]:
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
                    reason="manual_deletion",
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
