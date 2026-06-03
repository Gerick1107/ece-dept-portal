from __future__ import annotations

import threading
import tempfile
from pathlib import Path
from typing import Annotated
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.database.models.user import User, UserRole
from app.database.session import get_db
from app.publications.exports.export_service import (
    export_publications_grouped_archive,
    export_publications_csv,
    export_publications_excel,
    export_publications_pdf,
)
from app.publications.models import Faculty, Publication, ScrapeLog
from app.publications.schemas import (
    BulkDeleteRequest,
    CsvImportSummary,
    DeletionResponse,
    FacultyCreate,
    FacultyListResponse,
    FacultyResponse,
    FacultyUpdate,
    PublicationCreate,
    PublicationListResponse,
    PublicationResponse,
    PublicationUpdate,
    ScrapeTriggerRequest,
    ScrapeTriggerResponse,
    SyncAllResponse,
)
from app.publications.scheduler.jobs import scheduler_status
from app.publications.services.gap_fill_service import run_gap_fill_background
from app.publications.scraper.scholar_scraper import sync_faculty_publications
from app.publications.services.faculty_import_service import import_faculty_csv
from app.publications.services.publication_service import (
    create_faculty,
    create_publication,
    delete_publications,
    list_faculty,
    list_publications,
    publication_faculty_ids,
    publication_faculty_ids_map,
    update_faculty,
    update_publication,
)

router = APIRouter(prefix="/publications", tags=["publications"])


def _run_scrape_for_faculty_ids(faculty_ids: list[int], force: bool) -> None:
    from app.database.session import SessionLocal

    for faculty_id in faculty_ids:
        db = SessionLocal()
        try:
            faculty = db.scalar(select(Faculty).where(Faculty.id == faculty_id))
            if faculty is None:
                continue
            try:
                sync_faculty_publications(db, faculty, force=force)
            except Exception:
                continue
        finally:
            db.close()


def _to_faculty_response(item: Faculty, total_publications: int) -> FacultyResponse:
    return FacultyResponse.model_validate(
        {
            **item.__dict__,
            "total_publications": total_publications,
        }
    )


def _to_publication_response(db: Session, item: Publication) -> PublicationResponse:
    return PublicationResponse.model_validate(
        {
            **item.__dict__,
            "faculty_ids": publication_faculty_ids(db, item.id),
        }
    )


def _to_publication_responses(db: Session, items: list[Publication]) -> list[PublicationResponse]:
    faculty_map = publication_faculty_ids_map(db, [item.id for item in items])
    return [
        PublicationResponse.model_validate(
            {
                **item.__dict__,
                "faculty_ids": faculty_map.get(item.id, []),
            }
        )
        for item in items
    ]


def _mark_stale_scrapes_as_failed(db: Session, max_age_minutes: int = 3) -> int:
    cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)
    stale = db.scalars(
        select(ScrapeLog).where(
            ScrapeLog.status == "started",
            ScrapeLog.started_at < cutoff,
        )
    ).all()
    for row in stale:
        row.status = "failed"
        row.errors = "Scrape timed out"
        row.completed_at = datetime.utcnow()
    if stale:
        db.commit()
    return len(stale)


@router.get("/faculty", response_model=FacultyListResponse)
def get_faculty(
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    search: str | None = None,
    department: str | None = None,
    include_inactive: bool = False,
):
    rows, total = list_faculty(db, page, page_size, search, department, include_inactive)
    items = [_to_faculty_response(item, total_publications) for item, total_publications in rows]
    return FacultyListResponse(
        items=items,
        pagination={"page": page, "page_size": page_size, "total": total},
    )


@router.post("/faculty", response_model=FacultyResponse, status_code=status.HTTP_201_CREATED)
def add_faculty(
    body: FacultyCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    existing = db.scalar(select(Faculty).where(Faculty.scholar_id == body.scholar_id))
    if existing:
        raise HTTPException(status_code=409, detail="scholar_id already exists")
    item = create_faculty(db, body)
    return _to_faculty_response(item, 0)


@router.patch("/faculty/{faculty_id}", response_model=FacultyResponse)
def edit_faculty(
    faculty_id: int,
    body: FacultyUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    item = db.scalar(select(Faculty).where(Faculty.id == faculty_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Faculty not found")
    item = update_faculty(db, item, body)
    total_publications = len(item.publication_links)
    return _to_faculty_response(item, total_publications)


@router.post("/faculty/import-csv", response_model=CsvImportSummary)
async def upload_faculty_csv(
    csv_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    # TODO: restore admin auth dependency after development verification.
    # _: User = Depends(require_roles(UserRole.admin)),
):
    suffix = Path(csv_file.filename or "faculty_master.csv").suffix.lower()
    if suffix != ".csv":
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")
    with tempfile.NamedTemporaryFile(prefix="faculty_upload_", suffix=".csv", delete=False) as temp_file:
        tmp_path = Path(temp_file.name)
        temp_file.write(await csv_file.read())
    try:
        result = import_faculty_csv(db, tmp_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    # Import should stay fast. Scraping is triggered via /scrape/trigger only.
    return result


@router.get("/publications", response_model=PublicationListResponse)
def get_publications(
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    query: str | None = None,
    faculty_id: int | None = None,
    publication_year: int | None = None,
    is_patent: bool | None = None,
):
    items, total = list_publications(
        db,
        page,
        page_size,
        query=query,
        faculty_id=faculty_id,
        publication_year=publication_year,
        is_patent=is_patent,
    )
    return PublicationListResponse(
        items=_to_publication_responses(db, items),
        pagination={"page": page, "page_size": page_size, "total": total},
    )


@router.post("/publications", response_model=PublicationResponse, status_code=status.HTTP_201_CREATED)
def add_publication(
    body: PublicationCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    try:
        item = create_publication(db, body)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _to_publication_response(db, item)


@router.patch("/publications/{publication_id}", response_model=PublicationResponse)
def edit_publication(
    publication_id: int,
    body: PublicationUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    item = db.scalar(select(Publication).where(Publication.id == publication_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Publication not found")
    item = update_publication(db, item, body)
    return _to_publication_response(db, item)


@router.delete("/publications/{publication_id}", response_model=DeletionResponse)
def remove_publication(
    publication_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    deleted_count, blocked = delete_publications(db, [publication_id])
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="Publication not found")
    return DeletionResponse(deleted_count=deleted_count, blocked_hashes_added=blocked)


@router.post("/publications/delete-bulk", response_model=DeletionResponse)
def remove_publications_bulk(
    body: BulkDeleteRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    deleted_count, blocked = delete_publications(db, body.publication_ids)
    return DeletionResponse(deleted_count=deleted_count, blocked_hashes_added=blocked)


@router.post("/scrape/sync-all", response_model=SyncAllResponse)
def sync_all_publications(
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    worker = threading.Thread(target=run_gap_fill_background, daemon=True)
    worker.start()
    return SyncAllResponse(status="started", message="Sync running in background.")


@router.post("/scrape/trigger", response_model=ScrapeTriggerResponse)
def trigger_scrape(
    body: ScrapeTriggerRequest,
    db: Annotated[Session, Depends(get_db)],
    # TODO: restore admin auth dependency after development verification.
    # _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    _mark_stale_scrapes_as_failed(db)
    if body.faculty_id:
        rows = db.scalars(select(Faculty).where(Faculty.id == body.faculty_id)).all()
    else:
        if body.force:
            rows = db.scalars(select(Faculty)).all()
        else:
            rows = db.scalars(select(Faculty).where(Faculty.is_active.is_(True))).all()
    queued: list[int] = []
    queued = [row.id for row in rows]
    if queued:
        worker = threading.Thread(
            target=_run_scrape_for_faculty_ids,
            args=(queued, body.force),
            daemon=True,
        )
        worker.start()
    return ScrapeTriggerResponse(message="Scrape jobs queued", queued_faculty_ids=queued)


@router.get("/scrape/logs")
def get_scrape_logs(
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
):
    _mark_stale_scrapes_as_failed(db)
    stmt = (
        select(ScrapeLog, Faculty.name)
        .join(Faculty, Faculty.id == ScrapeLog.faculty_id)
        .order_by(ScrapeLog.started_at.desc())
    )
    total = db.scalar(select(func.count()).select_from(ScrapeLog)) or 0
    rows = db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return {
        "items": [
            {
                "id": log.id,
                "faculty_id": log.faculty_id,
                "faculty_name": faculty_name,
                "status": log.status,
                "new_publications_added": log.new_publications_added,
                "started_at": log.started_at,
                "completed_at": log.completed_at,
                "errors": log.errors,
            }
            for log, faculty_name in rows
        ],
        "pagination": {"page": page, "page_size": page_size, "total": int(total)},
    }


@router.get("/scheduler/status")
def get_scheduler_status():
    return scheduler_status()


@router.get("/exports")
def export_publications(
    format: str = Query(default="csv", pattern="^(csv|xlsx|pdf)$"),
    scope: str = Query(default="all", pattern="^(all|faculty|year)$"),
    export_type: str = Query(default="both", pattern="^(publications|patents|both)$"),
    faculty_id: int | None = None,
    faculty_ids: str | None = None,
    publication_year: int | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role not in (UserRole.admin, UserRole.faculty, UserRole.hod):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if year_start is not None and year_end is not None and year_start > year_end:
        raise HTTPException(status_code=400, detail="year_start cannot be greater than year_end")

    parsed_faculty_ids: list[int] = []
    if faculty_ids:
        try:
            parsed_faculty_ids = sorted(
                {
                    int(part.strip())
                    for part in faculty_ids.split(",")
                    if part.strip()
                }
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="faculty_ids must be a comma-separated list of integers") from exc
    if faculty_id is not None:
        parsed_faculty_ids.append(faculty_id)
    parsed_faculty_ids = sorted(set(parsed_faculty_ids))

    base_name = "publications"
    if parsed_faculty_ids:
        joined = "-".join(str(fid) for fid in parsed_faculty_ids)
        base_name += f"_faculty_{joined}"
    if publication_year:
        base_name += f"_year_{publication_year}"
    if year_start is not None or year_end is not None:
        base_name += f"_range_{year_start or 'min'}_{year_end or 'max'}"

    if scope in {"faculty", "year"} and format in {"csv", "pdf"}:
        payload = export_publications_grouped_archive(
            db,
            format=format,
            scope=scope,
            faculty_ids=parsed_faculty_ids or None,
            publication_year=publication_year,
            year_start=year_start,
            year_end=year_end,
            export_type=export_type,
        )
        return Response(
            content=payload,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={base_name}_{scope}_{format}.zip"},
        )

    if format == "pdf":
        title = f"Publications — {scope}"
        if publication_year:
            title += f" ({publication_year})"
        payload = export_publications_pdf(
            db,
            faculty_ids=parsed_faculty_ids or None,
            publication_year=publication_year,
            year_start=year_start,
            year_end=year_end,
            title=title,
            export_type=export_type,
        )
        return Response(
            content=payload,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={base_name}.pdf"},
        )
    if format == "xlsx":
        payload = export_publications_excel(
            db,
            faculty_ids=parsed_faculty_ids or None,
            publication_year=publication_year,
            year_start=year_start,
            year_end=year_end,
            scope=scope,
            export_type=export_type,
        )
        return Response(
            content=payload,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={base_name}.xlsx"},
        )
    payload = export_publications_csv(
        db,
        faculty_ids=parsed_faculty_ids or None,
        publication_year=publication_year,
        year_start=year_start,
        year_end=year_end,
        export_type=export_type,
    )
    return Response(
        content=payload,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={base_name}.csv"},
    )
