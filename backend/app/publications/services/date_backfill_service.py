"""Fill in exact publication dates without spending SerpAPI quota.

Google Scholar's own dates come from ``citation_*`` meta tags that publishers
(IEEE, Springer, ScienceDirect, ACM, MDPI, …) embed in the article page. Those
pages are ordinary URLs, so we can fetch them with plain HTTP — no API key, no
quota — for both the existing backlog and future syncs.

Resolution order (cheapest / most reliable first):
  1. Publisher page ``citation_publication_date`` / ``citation_date`` /
     ``citation_online_date`` meta tags (this is exactly what Scholar reads).
  2. Crossref REST API by title (free, no key).
  3. Optional local LLM as a last resort to read a date out of the page text.
"""
from __future__ import annotations

import logging
import re

import httpx
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.publications.models import Publication
from app.publications.utils.dates import parse_precision

logger = logging.getLogger(__name__)

_PRECISION_RANK = {None: 0, "year": 1, "month": 2, "day": 3}

# Meta tags publishers use, in order of preference (most precise first).
_META_DATE_KEYS = (
    "citation_publication_date",
    "citation_date",
    "citation_cover_date",
    "citation_online_date",
    "prism.publicationdate",
    "dc.date",
    "dcterms.date",
    "article:published_time",
)

_USER_AGENT = (
    "Mozilla/5.0 (compatible; ECE-Portal-DateBackfill/1.0; +https://ece.iiitd.ac.in)"
)


def _meta_re(name: str) -> re.Pattern[str]:
    # Matches <meta name="..." content="..."> in either attribute order.
    return re.compile(
        rf'<meta[^>]+(?:name|property)=["\']{re.escape(name)}["\'][^>]*?content=["\']([^"\']+)["\']'
        rf'|<meta[^>]+content=["\']([^"\']+)["\'][^>]*?(?:name|property)=["\']{re.escape(name)}["\']',
        re.IGNORECASE,
    )


def _extract_meta_date(html: str) -> tuple[str | None, str | None]:
    for key in _META_DATE_KEYS:
        m = _meta_re(key).search(html)
        if not m:
            continue
        raw = (m.group(1) or m.group(2) or "").strip()
        parsed, precision = parse_precision(raw)
        if parsed is not None:
            return parsed.isoformat(), precision
    return None, None


def _from_publisher_page(client: httpx.Client, url: str) -> tuple[str | None, str | None]:
    try:
        resp = client.get(url, follow_redirects=True, timeout=15.0)
        if resp.status_code != 200 or not resp.text:
            return None, None
        return _extract_meta_date(resp.text)
    except Exception as exc:  # network/parse failures are expected and non-fatal
        logger.debug("Publisher page fetch failed for %s: %s", url, exc)
        return None, None


def _from_crossref(client: httpx.Client, title: str) -> tuple[str | None, str | None]:
    if not title.strip():
        return None, None
    try:
        resp = client.get(
            "https://api.crossref.org/works",
            params={"query.bibliographic": title, "rows": 1},
            timeout=15.0,
        )
        if resp.status_code != 200:
            return None, None
        items = resp.json().get("message", {}).get("items", [])
        if not items:
            return None, None
        item = items[0]
        # Trust the match only if the returned title is close to ours.
        returned = (item.get("title") or [""])[0].strip().lower()
        if returned and returned[:40] != title.strip().lower()[:40]:
            return None, None
        for field in ("published-print", "published-online", "published", "issued", "created"):
            parts = (item.get(field) or {}).get("date-parts") or []
            if parts and parts[0]:
                dp = parts[0]
                year = dp[0]
                month = dp[1] if len(dp) > 1 else 1
                day = dp[2] if len(dp) > 2 else 1
                precision = "day" if len(dp) > 2 else "month" if len(dp) > 1 else "year"
                return f"{year:04d}-{month:02d}-{day:02d}", precision
    except Exception as exc:
        logger.debug("Crossref lookup failed for %r: %s", title[:60], exc)
    return None, None


def resolve_exact_date(
    publication: Publication, *, client: httpx.Client
) -> tuple[str | None, str | None]:
    """Return the most precise (iso_date, precision) found for a publication, or (None, None)."""
    best_date: str | None = None
    best_precision: str | None = None

    for url in (publication.link, publication.pdf_url):
        if not url:
            continue
        iso, precision = _from_publisher_page(client, url)
        if iso and _PRECISION_RANK[precision] > _PRECISION_RANK[best_precision]:
            best_date, best_precision = iso, precision
        if best_precision == "day":
            return best_date, best_precision

    iso, precision = _from_crossref(client, publication.title or "")
    if iso and _PRECISION_RANK[precision] > _PRECISION_RANK[best_precision]:
        best_date, best_precision = iso, precision

    return best_date, best_precision


def needs_exact_date(publication: Publication) -> bool:
    """True when the stored date is missing or coarser than full day precision."""
    _, precision = parse_precision(publication.publication_date)
    return _PRECISION_RANK[precision] < _PRECISION_RANK["day"]


def _candidate_publications(db: Session, limit: int | None) -> list[Publication]:
    stmt = (
        select(Publication)
        .where(Publication.is_patent.is_(False))
        .where(
            or_(
                Publication.link.is_not(None),
                Publication.pdf_url.is_not(None),
                Publication.title.is_not(None),
            )
        )
        .order_by(Publication.id.asc())
    )
    rows = [p for p in db.scalars(stmt).all() if needs_exact_date(p)]
    if limit is not None:
        rows = rows[:limit]
    return rows


def backfill_publication_dates(*, limit: int | None = None, delay_seconds: float = 0.5) -> dict:
    """Iterate publications lacking a full date and fill them from publisher/Crossref.

    No SerpAPI usage. Safe to run repeatedly; only upgrades to a more precise date.
    Returns a summary dict.
    """
    import time

    updated = 0
    checked = 0
    db = SessionLocal()
    try:
        candidates = _candidate_publications(db, limit)
        with httpx.Client(headers={"User-Agent": _USER_AGENT}) as client:
            for pub in candidates:
                checked += 1
                _, current_precision = parse_precision(pub.publication_date)
                iso, precision = resolve_exact_date(pub, client=client)
                if iso and _PRECISION_RANK[precision] > _PRECISION_RANK[current_precision]:
                    from app.publications.services.publication_service import (
                        apply_updates_respecting_overrides,
                    )

                    applied = apply_updates_respecting_overrides(
                        pub, {"publication_date": iso}
                    )
                    if applied:
                        updated += 1
                        db.commit()
                if delay_seconds > 0:
                    time.sleep(delay_seconds)
    finally:
        db.close()
    summary = {"checked": checked, "updated": updated}
    logger.info("Date backfill complete: %s", summary)
    return summary


def run_date_backfill_background(limit: int | None = None) -> None:
    backfill_publication_dates(limit=limit)
