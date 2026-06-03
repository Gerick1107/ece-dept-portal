from __future__ import annotations

import logging
import random
import subprocess
import sys
import time
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.publications.constants.defaults import (
    SCRAPE_STATUS_COMPLETED,
    SCRAPE_STATUS_FAILED,
    SCRAPE_STATUS_STARTED,
)
from app.config import get_settings
from app.publications.models import BlockedPublication, Faculty, Publication, PublicationFaculty, ScrapeLog
from app.publications.scraper.serpapi_scraper import scrape_faculty_serpapi
from app.publications.utils.helpers import is_within_tenure, make_source_hash

logger = logging.getLogger(__name__)
settings = get_settings()

try:
    from scholarly import scholarly
except Exception:  # pragma: no cover
    scholarly = None


def _normalize_pub(pub: dict) -> dict:
    bib = pub.get("bib", {}) if isinstance(pub, dict) else {}
    year_raw = bib.get("pub_year")
    try:
        year = int(year_raw) if year_raw else None
    except ValueError:
        year = None

    title = (bib.get("title") or "").strip()
    venue = (bib.get("venue") or "").strip() or None
    return {
        "title": title,
        "authors": (bib.get("author") or "").strip() or None,
        "publication_year": year,
        "journal": venue,
        "publisher": (bib.get("publisher") or "").strip() or None,
        "citation_count": int(pub.get("num_citations") or 0),
        "is_patent": False,
        "scholar_url": pub.get("pub_url") or pub.get("eprint_url"),
        "link": pub.get("pub_url") or pub.get("eprint_url"),
        "pdf_url": pub.get("eprint_url"),
    }


def _fetch_author_payload(scholar_id: str, timeout_seconds: int = 45) -> dict:
    script = (
        "import json\n"
        "from scholarly import scholarly\n"
        f"author=scholarly.search_author_id('{scholar_id}')\n"
        "author=scholarly.fill(author, sections=['indices','publications'])\n"
        "print(json.dumps(author, default=str))\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()[:400]
        raise RuntimeError(stderr or "scholarly subprocess failed")
    output = (proc.stdout or "").strip()
    if not output:
        raise RuntimeError("scholarly subprocess returned empty output")
    import json

    return json.loads(output)


def _ingest_publications(db: Session, faculty: Faculty, normalized_items: list[dict]) -> int:
    inserted = 0
    linked_publication_ids: set[int] = set()
    for normalized in normalized_items:
        title = normalized.get("title")
        if not title:
            continue

        year = normalized.get("publication_year")
        source_hash = make_source_hash(title, year)
        blocked = db.scalar(select(BlockedPublication).where(BlockedPublication.source_hash == source_hash))
        if blocked:
            continue
        if not is_within_tenure(faculty.join_year, faculty.leave_year, year):
            continue

        existing = db.scalar(select(Publication).where(Publication.source_hash == source_hash))
        if existing is None:
            existing = Publication(
                source_hash=source_hash,
                is_iiitd_publication=True,
                **normalized,
            )
            db.add(existing)
            db.flush()
            inserted += 1

        if existing.id in linked_publication_ids:
            continue

        mapping_exists = db.scalar(
            select(PublicationFaculty).where(
                PublicationFaculty.faculty_id == faculty.id,
                PublicationFaculty.publication_id == existing.id,
            )
        )
        if mapping_exists is None:
            db.add(PublicationFaculty(faculty_id=faculty.id, publication_id=existing.id))
        linked_publication_ids.add(existing.id)

    return inserted


def _sync_via_serpapi(db: Session, faculty: Faculty) -> int:
    payload = scrape_faculty_serpapi(faculty.scholar_id, settings.serp_api_key)
    metrics = payload["profile_metrics"]
    faculty.total_citations = int(metrics.get("total_citations") or 0)
    faculty.h_index = int(metrics.get("h_index") or 0)
    faculty.i10_index = int(metrics.get("i10_index") or 0)
    return _ingest_publications(db, faculty, payload["articles"])


def _sync_via_scholarly(db: Session, faculty: Faculty) -> int:
    if scholarly is None:
        raise RuntimeError("scholarly is not installed; add it to backend requirements")

    delay_min = float(getattr(settings, "publications_scrape_delay_min_seconds", 3.0))
    delay_max = float(getattr(settings, "publications_scrape_delay_max_seconds", 8.0))
    time.sleep(random.uniform(delay_min, delay_max))
    author = None
    last_error: Exception | None = None
    for _ in range(3):
        try:
            author = _fetch_author_payload(faculty.scholar_id, timeout_seconds=45)
            break
        except Exception as exc:
            last_error = exc
        time.sleep(random.uniform(delay_min, delay_max))
    if author is None:
        raise RuntimeError(f"Unable to fetch scholar profile for {faculty.scholar_id}: {last_error}")

    faculty.total_citations = int(author.get("citedby") or 0)
    faculty.h_index = int(author.get("hindex") or 0)
    faculty.i10_index = int(author.get("i10index") or 0)

    normalized_items: list[dict] = []
    for pub_ref in author.get("publications", []):
        time.sleep(random.uniform(delay_min, delay_max))
        pub = scholarly.fill(pub_ref)
        normalized_items.append(_normalize_pub(pub))

    return _ingest_publications(db, faculty, normalized_items)


def sync_faculty_publications(db: Session, faculty: Faculty, force: bool = False) -> int:
    faculty = db.merge(faculty)

    if not force and not faculty.is_active:
        return 0

    log = ScrapeLog(
        faculty_id=faculty.id,
        status=SCRAPE_STATUS_STARTED,
        started_at=datetime.utcnow(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    inserted = 0
    try:
        backend = (settings.scraper_backend or "scholarly").strip().lower()
        if backend == "serpapi":
            inserted = _sync_via_serpapi(db, faculty)
        else:
            inserted = _sync_via_scholarly(db, faculty)

        log.status = SCRAPE_STATUS_COMPLETED
        log.new_publications_added = inserted
        log.completed_at = datetime.utcnow()
        db.add(log)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Scholar sync failed for faculty_id=%s", faculty.id)
        failed_log = db.get(ScrapeLog, log.id)
        if failed_log is not None:
            failed_log.status = SCRAPE_STATUS_FAILED
            failed_log.errors = str(exc)
            failed_log.completed_at = datetime.utcnow()
            db.add(failed_log)
            db.commit()
        raise

    return inserted
