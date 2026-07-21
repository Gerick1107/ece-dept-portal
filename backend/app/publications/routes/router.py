from __future__ import annotations

import threading
import tempfile
from pathlib import Path
from typing import Annotated
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    FacultyScope,
    FacultyScopeDep,
    get_current_user,
    get_faculty_scope,
    require_roles,
)
from app.database.models.user import User, UserRole
from app.database.session import get_db
from app.publications.exports.export_service import (
    export_publications_grouped_archive,
    export_publications_csv,
    export_publications_docx,
    export_publications_excel,
    export_publications_pdf,
)
from app.publications.models import Faculty, Publication, ScrapeLog
from app.publications.schemas import (
    BulkDeleteRequest,
    CsvImportSummary,
    CustomColumnCreate,
    CustomColumnResponse,
    CustomColumnSuggestRequest,
    CustomColumnUpdate,
    DeletionResponse,
    FacultyAffiliationsResponse,
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
    StudentPublicationCreate,
    StudentPublicationImportSummary,
    StudentPublicationListResponse,
    StudentPublicationResponse,
    SyncAllResponse,
)
from app.publications.scheduler.jobs import scheduler_status
from app.publications.services.gap_fill_service import run_gap_fill_background
from app.publications.scraper.scholar_scraper import sync_faculty_publications
from app.publications.services.affiliations_import_service import import_faculty_affiliations, list_faculty_affiliations
from app.publications.services.faculty_import_service import import_faculty_csv
from app.publications.services.publication_service import (
    create_faculty,
    create_publication,
    delete_publications,
    list_faculty,
    list_publications,
    publication_faculty_ids,
    publication_faculty_ids_map,
    purge_repository_publications,
    update_faculty,
    update_publication,
    user_can_manage_publication,
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
    from app.publications.services.custom_columns_service import get_custom_fields
    from app.publications.services.publication_service import get_manual_overrides

    return PublicationResponse.model_validate(
        {
            **item.__dict__,
            "faculty_ids": publication_faculty_ids(db, item.id),
            "custom_fields": get_custom_fields(item),
            "manual_overrides": get_manual_overrides(item),
            "is_manual_book": bool(getattr(item, "is_manual_book", False)),
        }
    )


def _to_publication_responses(db: Session, items: list[Publication]) -> list[PublicationResponse]:
    from app.publications.services.custom_columns_service import get_custom_fields
    from app.publications.services.publication_service import get_manual_overrides

    faculty_map = publication_faculty_ids_map(db, [item.id for item in items])
    return [
        PublicationResponse.model_validate(
            {
                **item.__dict__,
                "faculty_ids": faculty_map.get(item.id, []),
                "custom_fields": get_custom_fields(item),
                "manual_overrides": get_manual_overrides(item),
                "is_manual_book": bool(getattr(item, "is_manual_book", False)),
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
    scope: FacultyScopeDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    search: str | None = None,
    department: str | None = None,
    include_inactive: bool = False,
):
    rows, total = list_faculty(db, page, page_size, search, department, include_inactive)
    # Non-admins only ever see their own directory entry.
    if not scope.see_all:
        rows = [pair for pair in rows if pair[0].id == scope.faculty_id]
        total = len(rows)
    items = [_to_faculty_response(item, total_publications) for item, total_publications in rows]
    return FacultyListResponse(
        items=items,
        pagination={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/faculty/{faculty_id}/affiliations", response_model=FacultyAffiliationsResponse)
def get_faculty_affiliations(
    faculty_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    # Keep affiliations in sync with Links.txt on normal page refreshes.
    try:
        import_faculty_affiliations(db)
    except Exception:
        # Non-blocking: still return currently persisted affiliations.
        pass
    faculty = db.scalar(select(Faculty).where(Faculty.id == faculty_id))
    if faculty is None:
        raise HTTPException(status_code=404, detail="Faculty not found")
    items = list_faculty_affiliations(db, faculty_id)
    return FacultyAffiliationsResponse(
        faculty_id=faculty_id,
        faculty_name=faculty.name,
        items=items,
    )


@router.post("/faculty", response_model=FacultyResponse, status_code=status.HTTP_201_CREATED)
def add_faculty(
    body: FacultyCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    from app.publications.utils.helpers import normalize_scholar_id

    scholar_id = normalize_scholar_id(body.scholar_id)
    if not scholar_id:
        raise HTTPException(status_code=400, detail="scholar_id is required")
    existing = db.scalar(select(Faculty).where(Faculty.scholar_id == scholar_id))
    if existing:
        raise HTTPException(status_code=409, detail="scholar_id already exists")
    try:
        # Persist normalized id.
        body = body.model_copy(update={"scholar_id": scholar_id})
        item = create_faculty(db, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
    _: User = Depends(require_roles(UserRole.admin)),
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
    scope: FacultyScopeDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    query: str | None = None,
    search_by: str = Query(default="title", pattern="^(title|venue)$"),
    faculty_id: int | None = None,
    publication_year: int | None = None,
    is_patent: bool | None = None,
    category: str | None = Query(
        default=None,
        pattern="^(journals|conferences|book_chapters|books|preprints)$",
    ),
):
    # Non-admins are locked to their own publications regardless of the param.
    if not scope.see_all:
        if scope.is_empty:
            return PublicationListResponse(
                items=[], pagination={"page": page, "page_size": page_size, "total": 0}
            )
        faculty_id = scope.faculty_id
    items, total = list_publications(
        db,
        page,
        page_size,
        query=query,
        faculty_id=faculty_id,
        publication_year=publication_year,
        is_patent=is_patent,
        search_by=search_by,
        category=category,
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
    user: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.faculty, UserRole.hod))],
    scope: FacultyScopeDep,
):
    item = db.scalar(select(Publication).where(Publication.id == publication_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Publication not found")
    if not user_can_manage_publication(
        db, publication_id=publication_id, faculty_id=scope.faculty_id, see_all=scope.see_all
    ):
        raise HTTPException(status_code=403, detail="You can only edit your own publications")
    item = update_publication(db, item, body)
    return _to_publication_response(db, item)


@router.delete("/publications/{publication_id}", response_model=DeletionResponse)
def remove_publication(
    publication_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.faculty, UserRole.hod))],
    scope: FacultyScopeDep,
):
    item = db.scalar(select(Publication).where(Publication.id == publication_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Publication not found")
    if not user_can_manage_publication(
        db, publication_id=publication_id, faculty_id=scope.faculty_id, see_all=scope.see_all
    ):
        raise HTTPException(status_code=403, detail="You can only delete your own publications")
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
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    # Defensive cleanup before background sync so UI/export never keep repository links.
    try:
        purge_repository_publications(db)
    except Exception:
        pass
    worker = threading.Thread(target=run_gap_fill_background, daemon=True)
    worker.start()
    return SyncAllResponse(
        status="started",
        message=(
            "Sync running in background. New publications and patents will be fetched from "
            "Google Scholar profiles, enriched with full metadata, and saved to the database. "
            "Publications linking to repository.iiitd.edu.in are excluded. "
            "Refresh Scrape Logs for progress."
        ),
    )


@router.post("/scrape/backfill-dates", response_model=SyncAllResponse)
def backfill_dates(
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    from app.publications.services.date_backfill_service import run_date_backfill_background

    worker = threading.Thread(target=run_date_backfill_background, daemon=True)
    worker.start()
    return SyncAllResponse(
        status="started",
        message=(
            "Backfilling exact publication dates in the background. This reads publisher "
            "pages and Crossref (no SerpAPI usage) for publications missing a full date. "
            "Refresh in a while to see updated dates."
        ),
    )


@router.get("/custom-columns", response_model=list[CustomColumnResponse])
def list_custom_columns(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    from app.publications.services.custom_columns_service import list_columns

    return list_columns(db)


@router.post("/custom-columns", response_model=CustomColumnResponse, status_code=status.HTTP_201_CREATED)
def add_custom_column(
    body: CustomColumnCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    from app.publications.services.custom_columns_service import create_column

    try:
        return create_column(
            db,
            label=body.label,
            description=body.description,
            source_keys=body.source_keys,
            crossref_field=body.crossref_field,
            use_llm=body.use_llm,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/custom-columns/{column_id}", response_model=CustomColumnResponse)
def edit_custom_column(
    column_id: int,
    body: CustomColumnUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    from app.publications.services.custom_columns_service import update_column

    col = update_column(db, column_id, **body.model_dump(exclude_unset=True))
    if col is None:
        raise HTTPException(status_code=404, detail="Custom column not found")
    return col


@router.delete("/custom-columns/{column_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_custom_column(
    column_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    from app.publications.services.custom_columns_service import delete_column

    if not delete_column(db, column_id):
        raise HTTPException(status_code=404, detail="Custom column not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/custom-columns/suggest")
async def suggest_custom_column(
    body: CustomColumnSuggestRequest,
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    """Use the local LLM to suggest publisher meta-tag names / Crossref field for
    a desired column. The admin reviews and edits before saving the column."""
    from app.publications.services.custom_columns_service import suggest_column_sources

    return await suggest_column_sources(body.label, body.description)


@router.post("/custom-columns/backfill", response_model=SyncAllResponse)
def backfill_custom_columns_endpoint(
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    from app.publications.services.custom_columns_service import run_custom_backfill_background

    worker = threading.Thread(target=run_custom_backfill_background, daemon=True)
    worker.start()
    return SyncAllResponse(
        status="started",
        message=(
            "Backfilling custom columns in the background. This reads publisher pages and "
            "Crossref (no SerpAPI usage) for publications missing these values. Refresh the "
            "publications table in a while to see the filled columns."
        ),
    )


@router.post("/scrape/trigger", response_model=ScrapeTriggerResponse)
def trigger_scrape(
    body: ScrapeTriggerRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
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
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
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

    def _iso(dt: datetime | None) -> str | None:
        if dt is None:
            return None
        return dt.isoformat()

    return {
        "items": [
            {
                "id": log.id,
                "faculty_id": log.faculty_id,
                "faculty_name": faculty_name,
                "status": log.status,
                "new_publications_added": log.new_publications_added,
                "started_at": _iso(log.started_at),
                "completed_at": _iso(log.completed_at),
                "errors": log.errors,
            }
            for log, faculty_name in rows
        ],
        "pagination": {"page": page, "page_size": page_size, "total": int(total)},
    }


@router.get("/scheduler/status")
def get_scheduler_status():
    return scheduler_status()


def _parse_export_date(value: str | None, field: str) -> "date | None":
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{field} must be in YYYY-MM-DD format") from exc


@router.get("/exports")
def export_publications(
    format: str = Query(default="csv", pattern="^(csv|xlsx|pdf|docx)$"),
    scope: str = Query(default="all", pattern="^(all|faculty|year)$"),
    export_type: str = Query(default="both", pattern="^(publications|patents|both)$"),
    faculty_id: int | None = None,
    faculty_ids: str | None = None,
    publication_year: int | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    faculty_scope: FacultyScope = Depends(get_faculty_scope),
):
    if user.role not in (UserRole.admin, UserRole.faculty, UserRole.hod):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if year_start is not None and year_end is not None and year_start > year_end:
        raise HTTPException(status_code=400, detail="year_start cannot be greater than year_end")
    parsed_date_start = _parse_export_date(date_start, "date_start")
    parsed_date_end = _parse_export_date(date_end, "date_end")
    if parsed_date_start and parsed_date_end and parsed_date_start > parsed_date_end:
        raise HTTPException(status_code=400, detail="date_start cannot be after date_end")

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

    # Non-admins can only export their own publications, regardless of params.
    if not faculty_scope.see_all:
        parsed_faculty_ids = [faculty_scope.faculty_id] if faculty_scope.faculty_id is not None else [-1]

    base_name = "publications"
    if parsed_faculty_ids:
        joined = "-".join(str(fid) for fid in parsed_faculty_ids)
        base_name += f"_faculty_{joined}"
    if publication_year:
        base_name += f"_year_{publication_year}"
    if year_start is not None or year_end is not None:
        base_name += f"_range_{year_start or 'min'}_{year_end or 'max'}"
    if parsed_date_start is not None or parsed_date_end is not None:
        base_name += f"_dates_{date_start or 'min'}_{date_end or 'max'}"

    if scope in {"faculty", "year"} and format in {"csv", "pdf"}:
        payload = export_publications_grouped_archive(
            db,
            format=format,
            scope=scope,
            faculty_ids=parsed_faculty_ids or None,
            publication_year=publication_year,
            year_start=year_start,
            year_end=year_end,
            date_start=parsed_date_start,
            date_end=parsed_date_end,
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
            date_start=parsed_date_start,
            date_end=parsed_date_end,
            title=title,
            export_type=export_type,
        )
        return Response(
            content=payload,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={base_name}.pdf"},
        )
    if format == "docx":
        title = f"Publications — {scope}"
        if publication_year:
            title += f" ({publication_year})"
        payload = export_publications_docx(
            db,
            faculty_ids=parsed_faculty_ids or None,
            publication_year=publication_year,
            year_start=year_start,
            year_end=year_end,
            date_start=parsed_date_start,
            date_end=parsed_date_end,
            title=title,
            export_type=export_type,
        )
        return Response(
            content=payload,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={base_name}.docx"},
        )
    if format == "xlsx":
        payload = export_publications_excel(
            db,
            faculty_ids=parsed_faculty_ids or None,
            publication_year=publication_year,
            year_start=year_start,
            year_end=year_end,
            date_start=parsed_date_start,
            date_end=parsed_date_end,
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
        date_start=parsed_date_start,
        date_end=parsed_date_end,
        export_type=export_type,
    )
    return Response(
        content=payload,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={base_name}.csv"},
    )


_TEMPLATE_MAX_BYTES = 5 * 1024 * 1024
_TEMPLATE_MEDIA = {
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.post("/exports/template/analyze")
async def analyze_export_template(
    template: UploadFile = File(...),
    use_llm: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Inspect an uploaded template's columns and propose a field mapping for review."""
    if user.role not in (UserRole.admin, UserRole.faculty, UserRole.hod):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    from app.publications.exports.custom_export_service import (
        CANONICAL_FIELDS,
        TemplateError,
        extract_headers,
        llm_guess_fields,
        match_headers,
    )
    from app.publications.services.custom_columns_service import list_columns

    content = await template.read()
    if len(content) > _TEMPLATE_MAX_BYTES:
        raise HTTPException(status_code=400, detail="Template too large (max 5 MB)")
    try:
        headers, fmt = extract_headers(template.filename or "", content)
        result = match_headers(headers, db)
    except TemplateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    llm_guesses: dict[str, str] = {}
    if use_llm and result.unknown:
        llm_guesses = await llm_guess_fields(result.unknown)

    available = list(CANONICAL_FIELDS.keys()) + [f"custom:{c.key}" for c in list_columns(db, enabled_only=True)]
    return {
        "format": fmt,
        "headers": headers,
        "matched": result.matched,
        "suggestions": result.suggestions,
        "unknown": [h for h in result.unknown if h not in llm_guesses],
        "llm_guesses": llm_guesses,
        "available_fields": available,
    }


@router.post("/exports/template/compile")
async def compile_export_template(
    template: UploadFile = File(...),
    mapping: str = Form(...),
    export_type: str = Form(default="both"),
    faculty_ids: str | None = Form(default=None),
    publication_year: int | None = Form(default=None),
    year_start: int | None = Form(default=None),
    year_end: int | None = Form(default=None),
    date_start: str | None = Form(default=None),
    date_end: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: FacultyScope = Depends(get_faculty_scope),
):
    """Compile publication data into the uploaded template's columns/format."""
    if user.role not in (UserRole.admin, UserRole.faculty, UserRole.hod):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if export_type not in ("publications", "patents", "both"):
        raise HTTPException(status_code=400, detail="Invalid export_type")

    import json

    from app.publications.exports.custom_export_service import (
        TemplateError,
        compile_export,
        extract_headers,
    )

    try:
        mapping_dict = json.loads(mapping)
        if not isinstance(mapping_dict, dict):
            raise ValueError
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="mapping must be a JSON object") from exc

    parsed_faculty_ids: list[int] = []
    if faculty_ids:
        try:
            parsed_faculty_ids = sorted({int(p.strip()) for p in faculty_ids.split(",") if p.strip()})
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="faculty_ids must be comma-separated integers") from exc

    # Non-admins can only compile their own publications.
    if not scope.see_all:
        parsed_faculty_ids = [scope.faculty_id] if scope.faculty_id is not None else [-1]

    parsed_date_start = _parse_export_date(date_start, "date_start")
    parsed_date_end = _parse_export_date(date_end, "date_end")

    content = await template.read()
    if len(content) > _TEMPLATE_MAX_BYTES:
        raise HTTPException(status_code=400, detail="Template too large (max 5 MB)")
    try:
        headers, fmt = extract_headers(template.filename or "", content)
        payload = compile_export(
            db,
            headers=headers,
            mapping={h: mapping_dict[h] for h in headers if h in mapping_dict},
            fmt=fmt,
            faculty_ids=parsed_faculty_ids or None,
            publication_year=publication_year,
            year_start=year_start,
            year_end=year_end,
            date_start=parsed_date_start,
            date_end=parsed_date_end,
            export_type=export_type,
        )
    except TemplateError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return Response(
        content=payload,
        media_type=_TEMPLATE_MEDIA.get(fmt, "application/octet-stream"),
        headers={"Content-Disposition": f"attachment; filename=publications_custom.{fmt}"},
    )


_FIELDS_MEDIA = {
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.post("/exports/fields/analyze")
async def analyze_export_fields(
    fields_text: str = Form(...),
    use_llm: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Match user-typed column names to publication data fields."""
    if user.role not in (UserRole.admin, UserRole.faculty, UserRole.hod):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    from app.publications.exports.custom_export_service import (
        CANONICAL_FIELDS,
        TemplateError,
        llm_guess_fields,
        match_headers,
        parse_fields_from_text,
    )
    from app.publications.services.custom_columns_service import list_columns

    headers = parse_fields_from_text(fields_text)
    if not headers:
        raise HTTPException(status_code=400, detail="Enter at least one column name.")
    try:
        result = match_headers(headers, db)
    except TemplateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    llm_guesses: dict[str, str] = {}
    if use_llm and result.unknown:
        llm_guesses = await llm_guess_fields(result.unknown)

    available = list(CANONICAL_FIELDS.keys()) + [f"custom:{c.key}" for c in list_columns(db, enabled_only=True)]
    return {
        "format": "fields",
        "headers": headers,
        "matched": result.matched,
        "suggestions": result.suggestions,
        "unknown": [h for h in result.unknown if h not in llm_guesses],
        "llm_guesses": llm_guesses,
        "available_fields": available,
    }


@router.post("/exports/fields/compile")
async def compile_export_fields(
    mapping: str = Form(...),
    fields_text: str = Form(...),
    format: str = Form(default="xlsx"),
    export_type: str = Form(default="both"),
    faculty_ids: str | None = Form(default=None),
    publication_year: int | None = Form(default=None),
    year_start: int | None = Form(default=None),
    year_end: int | None = Form(default=None),
    date_start: str | None = Form(default=None),
    date_end: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: FacultyScope = Depends(get_faculty_scope),
):
    """Export publication data using a user-defined column list (no template upload)."""
    if user.role not in (UserRole.admin, UserRole.faculty, UserRole.hod):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if export_type not in ("publications", "patents", "both"):
        raise HTTPException(status_code=400, detail="Invalid export_type")

    import json

    from app.publications.exports.custom_export_service import (
        TemplateError,
        compile_fields_export,
        parse_fields_from_text,
    )

    fmt = (format or "xlsx").lower().strip()
    if fmt not in _FIELDS_MEDIA:
        raise HTTPException(status_code=400, detail="format must be csv, xlsx, pdf, or docx")

    try:
        mapping_dict = json.loads(mapping)
        if not isinstance(mapping_dict, dict):
            raise ValueError
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="mapping must be a JSON object") from exc

    headers = parse_fields_from_text(fields_text)
    if not headers:
        raise HTTPException(status_code=400, detail="Enter at least one column name.")

    parsed_faculty_ids: list[int] = []
    if faculty_ids:
        try:
            parsed_faculty_ids = sorted({int(p.strip()) for p in faculty_ids.split(",") if p.strip()})
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="faculty_ids must be comma-separated integers") from exc

    if not scope.see_all:
        parsed_faculty_ids = [scope.faculty_id] if scope.faculty_id is not None else [-1]

    parsed_date_start = _parse_export_date(date_start, "date_start")
    parsed_date_end = _parse_export_date(date_end, "date_end")

    try:
        payload = compile_fields_export(
            db,
            headers=headers,
            mapping={h: mapping_dict[h] for h in headers if h in mapping_dict},
            fmt=fmt,
            faculty_ids=parsed_faculty_ids or None,
            publication_year=publication_year,
            year_start=year_start,
            year_end=year_end,
            date_start=parsed_date_start,
            date_end=parsed_date_end,
            export_type=export_type,
        )
    except TemplateError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return Response(
        content=payload,
        media_type=_FIELDS_MEDIA.get(fmt, "application/octet-stream"),
        headers={"Content-Disposition": f"attachment; filename=publications_custom.{fmt}"},
    )


@router.get("/student-publications/template")
def download_student_publications_template(
    _: Annotated[User, Depends(get_current_user)],
):
    from app.publications.services.student_publications_service import build_student_publications_template

    payload = build_student_publications_template()
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=student_publications_template.xlsx"},
    )


@router.get("/student-publications", response_model=StudentPublicationListResponse)
def get_student_publications(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    title: str | None = None,
    authors: str | None = None,
    year: int | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
):
    from app.publications.services.student_publications_service import (
        list_student_publications,
        row_to_dict,
    )

    items, total, columns = list_student_publications(
        db,
        page=page,
        page_size=page_size,
        title_query=title,
        authors_query=authors,
        year=year,
        year_min=year_min,
        year_max=year_max,
        sort_dir=sort_dir,
    )
    return StudentPublicationListResponse(
        items=[StudentPublicationResponse.model_validate(row_to_dict(item)) for item in items],
        columns=columns,
        pagination={"page": page, "page_size": page_size, "total": total},
    )


@router.post(
    "/student-publications",
    response_model=StudentPublicationResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_student_publication(
    body: StudentPublicationCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    from app.publications.services.student_publications_service import (
        create_student_publication,
        row_to_dict,
    )

    try:
        item = create_student_publication(
            db,
            title=body.title,
            authors=body.authors,
            publication_year=body.publication_year,
            extra_fields=body.extra_fields,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StudentPublicationResponse.model_validate(row_to_dict(item))


@router.post("/student-publications/import", response_model=StudentPublicationImportSummary)
async def import_student_publications(
    excel_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin)),
):
    from app.publications.services.student_publications_service import import_student_publications_excel

    filename = excel_file.filename or "student_publications.xlsx"
    suffix = Path(filename).suffix.lower()
    if suffix not in {".xlsx", ".xls"}:
        raise HTTPException(status_code=400, detail="Only .xlsx or .xls files are accepted")
    content = await excel_file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    try:
        summary = import_student_publications_excel(db, content, filename)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StudentPublicationImportSummary(**summary)


@router.delete("/student-publications/{publication_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_student_publication(
    publication_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    from app.publications.services.student_publications_service import delete_student_publication

    if not delete_student_publication(db, publication_id):
        raise HTTPException(status_code=404, detail="Student publication not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
