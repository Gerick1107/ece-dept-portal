from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.session import SessionLocal
from app.publications.constants.defaults import SCRAPE_STATUS_COMPLETED, SCRAPE_STATUS_FAILED
from app.publications.models import BlockedPublication, Faculty, Publication, PublicationFaculty, ScrapeLog
from app.publications.scraper.serpapi_scraper import scrape_faculty_serpapi
from app.publications.utils.helpers import is_within_tenure, make_source_hash

logger = logging.getLogger(__name__)
settings = get_settings()

FACULTY_DELAY_SECONDS = 2.0


@dataclass
class FacultyGapFillResult:
    faculty_id: int
    faculty_name: str
    scholar_id: str
    fetched: int = 0
    already_in_db: int = 0
    newly_inserted: int = 0
    metrics_updated: bool = False
    status: str = SCRAPE_STATUS_COMPLETED
    error: str | None = None


@dataclass
class GapFillSummary:
    total_faculty_processed: int = 0
    total_new_publications: int = 0
    failed_faculty: list[str] = field(default_factory=list)
    results: list[FacultyGapFillResult] = field(default_factory=list)


def gap_fill_faculty(db: Session, faculty: Faculty) -> FacultyGapFillResult:
    """Fetch SerpAPI publications for one faculty; insert only missing source_hash rows."""
    result = FacultyGapFillResult(
        faculty_id=faculty.id,
        faculty_name=faculty.name,
        scholar_id=faculty.scholar_id,
    )
    log = ScrapeLog(
        faculty_id=faculty.id,
        status="started",
        started_at=datetime.utcnow(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    try:
        payload = scrape_faculty_serpapi(faculty.scholar_id, settings.serp_api_key)
        metrics = payload["profile_metrics"]
        faculty.total_citations = int(metrics.get("total_citations") or 0)
        faculty.h_index = int(metrics.get("h_index") or 0)
        faculty.i10_index = int(metrics.get("i10_index") or 0)
        result.metrics_updated = True

        for article in payload["articles"]:
            title = (article.get("title") or "").strip()
            if not title:
                continue
            year = article.get("publication_year")
            if not is_within_tenure(faculty.join_year, faculty.leave_year, year):
                continue

            result.fetched += 1
            source_hash = make_source_hash(title, year)

            blocked = db.scalar(
                select(BlockedPublication).where(BlockedPublication.source_hash == source_hash)
            )
            if blocked:
                result.already_in_db += 1
                continue

            existing = db.scalar(select(Publication).where(Publication.source_hash == source_hash))
            if existing is not None:
                result.already_in_db += 1
                continue

            publication = Publication(
                source_hash=source_hash,
                is_iiitd_publication=True,
                **article,
            )
            db.add(publication)
            db.flush()

            mapping_exists = db.scalar(
                select(PublicationFaculty).where(
                    PublicationFaculty.faculty_id == faculty.id,
                    PublicationFaculty.publication_id == publication.id,
                )
            )
            if mapping_exists is None:
                db.add(PublicationFaculty(faculty_id=faculty.id, publication_id=publication.id))

            result.newly_inserted += 1

        log.status = SCRAPE_STATUS_COMPLETED
        log.new_publications_added = result.newly_inserted
        log.completed_at = datetime.utcnow()
        log.errors = None
        db.add(log)
        db.commit()
        result.status = SCRAPE_STATUS_COMPLETED
    except Exception as exc:
        db.rollback()
        logger.exception("Gap-fill failed for faculty_id=%s", faculty.id)
        failed_log = db.get(ScrapeLog, log.id)
        if failed_log is not None:
            failed_log.status = SCRAPE_STATUS_FAILED
            failed_log.errors = str(exc)
            failed_log.completed_at = datetime.utcnow()
            db.add(failed_log)
            db.commit()
        result.status = SCRAPE_STATUS_FAILED
        result.error = str(exc)

    return result


def run_gap_fill_all(
    *,
    delay_seconds: float = FACULTY_DELAY_SECONDS,
    faculty_id_min: int = 1,
    faculty_id_max: int = 27,
) -> GapFillSummary:
    """Process faculty in faculty_id ASC order with a fresh session per faculty."""
    summary = GapFillSummary()
    faculty_ids = list(range(faculty_id_min, faculty_id_max + 1))
    total_slots = len(faculty_ids)

    for index, faculty_id in enumerate(faculty_ids, start=1):
        db = SessionLocal()
        try:
            faculty = db.scalar(select(Faculty).where(Faculty.id == faculty_id))
            if faculty is None:
                continue
            row = gap_fill_faculty(db, faculty)
            summary.results.append(row)
            summary.total_faculty_processed += 1
            summary.total_new_publications += row.newly_inserted
            if row.status == SCRAPE_STATUS_FAILED:
                summary.failed_faculty.append(row.faculty_name)

            print(
                f"[{index}/{total_slots}] {row.faculty_name} ({row.scholar_id})... "
                f"fetched: {row.fetched}, already_in_db: {row.already_in_db}, "
                f"newly_inserted: {row.newly_inserted}, "
                f"metrics {'updated' if row.metrics_updated else 'unchanged'}"
            )
        finally:
            db.close()

        if index < total_slots and delay_seconds > 0:
            time.sleep(delay_seconds)

    return summary


def run_gap_fill_background(
    faculty_id_min: int = 1,
    faculty_id_max: int = 27,
    delay_seconds: float = FACULTY_DELAY_SECONDS,
) -> None:
    run_gap_fill_all(
        delay_seconds=delay_seconds,
        faculty_id_min=faculty_id_min,
        faculty_id_max=faculty_id_max,
    )
