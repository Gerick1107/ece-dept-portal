from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.publications.constants.defaults import SCRAPE_STATUS_COMPLETED, SCRAPE_STATUS_FAILED
from app.publications.models import BlockedPublication, Faculty, Publication, PublicationFaculty, ScrapeLog
from app.publications.scraper.serpapi_scraper import SerpApiError, scrape_faculty_serpapi
from app.publications.services.enrichment_service import enrich_publication
from app.publications.services.serpapi_keys import SerpApiKeyManager, load_api_keys
from app.publications.utils.helpers import is_within_tenure, make_source_hash

logger = logging.getLogger(__name__)

FACULTY_DELAY_SECONDS = 2.0


@dataclass
class FacultyGapFillResult:
    faculty_id: int
    faculty_name: str
    scholar_id: str
    fetched: int = 0
    already_in_db: int = 0
    newly_inserted: int = 0
    enriched: int = 0
    metrics_updated: bool = False
    status: str = SCRAPE_STATUS_COMPLETED
    error: str | None = None


@dataclass
class GapFillSummary:
    total_faculty_processed: int = 0
    total_new_publications: int = 0
    total_enriched: int = 0
    failed_faculty: list[str] = field(default_factory=list)
    results: list[FacultyGapFillResult] = field(default_factory=list)
    keys_exhausted: bool = False


def _active_faculty_ids(db: Session) -> list[int]:
    return list(
        db.scalars(
            select(Faculty.id).where(Faculty.is_active.is_(True)).order_by(Faculty.id.asc())
        ).all()
    )


def gap_fill_faculty(
    db: Session,
    faculty: Faculty,
    *,
    key_manager: SerpApiKeyManager,
    client: httpx.Client,
) -> FacultyGapFillResult:
    """Fetch SerpAPI author profile; insert missing publications; enrich with view_citation metadata."""
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
        api_key = key_manager.current_key()
        if not api_key:
            raise SerpApiError("All SerpAPI keys are exhausted", 429)

        payload = scrape_faculty_serpapi(faculty.scholar_id, api_key)
        key_manager.record_use()

        metrics = payload["profile_metrics"]
        faculty.total_citations = int(metrics.get("total_citations") or 0)
        faculty.h_index = int(metrics.get("h_index") or 0)
        faculty.i10_index = int(metrics.get("i10_index") or 0)
        result.metrics_updated = True

        new_publications: list[Publication] = []

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
                mapping_exists = db.scalar(
                    select(PublicationFaculty).where(
                        PublicationFaculty.faculty_id == faculty.id,
                        PublicationFaculty.publication_id == existing.id,
                    )
                )
                if mapping_exists is None:
                    db.add(PublicationFaculty(faculty_id=faculty.id, publication_id=existing.id))
                continue

            publication = Publication(
                source_hash=source_hash,
                is_iiitd_publication=True,
                raw_metadata=None,
                **article,
            )
            db.add(publication)
            db.flush()
            db.add(PublicationFaculty(faculty_id=faculty.id, publication_id=publication.id))
            new_publications.append(publication)
            result.newly_inserted += 1

        for publication in new_publications:
            if key_manager.exhausted:
                break
            if enrich_publication(publication, client=client, key_manager=key_manager):
                result.enriched += 1

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
    faculty_ids: list[int] | None = None,
) -> GapFillSummary:
    """Process active faculty (or explicit id list) with SerpAPI key rotation."""
    summary = GapFillSummary()
    api_keys = load_api_keys()
    if not api_keys:
        logger.error("No SerpAPI keys configured (SERP_API_KEYS or SERP_API_KEY)")
        summary.keys_exhausted = True
        return summary

    key_manager = SerpApiKeyManager(api_keys)
    if key_manager.exhausted:
        summary.keys_exhausted = True
        return summary

    bootstrap_db = SessionLocal()
    try:
        target_ids = faculty_ids or _active_faculty_ids(bootstrap_db)
    finally:
        bootstrap_db.close()

    total_slots = len(target_ids)
    with httpx.Client(timeout=60.0) as client:
        for index, faculty_id in enumerate(target_ids, start=1):
            if key_manager.exhausted:
                summary.keys_exhausted = True
                logger.warning("Stopping gap-fill: SerpAPI keys exhausted")
                break

            db = SessionLocal()
            try:
                faculty = db.scalar(select(Faculty).where(Faculty.id == faculty_id))
                if faculty is None:
                    continue
                row = gap_fill_faculty(db, faculty, key_manager=key_manager, client=client)
                summary.results.append(row)
                summary.total_faculty_processed += 1
                summary.total_new_publications += row.newly_inserted
                summary.total_enriched += row.enriched
                if row.status == SCRAPE_STATUS_FAILED:
                    summary.failed_faculty.append(row.faculty_name)

                logger.info(
                    "[%s/%s] %s: fetched=%s new=%s enriched=%s",
                    index,
                    total_slots,
                    row.faculty_name,
                    row.fetched,
                    row.newly_inserted,
                    row.enriched,
                )
            finally:
                db.close()

            if index < total_slots and delay_seconds > 0:
                time.sleep(delay_seconds)

    summary.keys_exhausted = key_manager.exhausted
    return summary


def run_gap_fill_background(faculty_ids: list[int] | None = None) -> None:
    run_gap_fill_all(faculty_ids=faculty_ids)
