"""Admin-defined custom publication columns.

An admin can define extra columns (e.g. ISSN) that Google Scholar does not
provide directly but that are usually available on the publisher's page. Each
column stores the HTML ``<meta>`` tag names to look for and, optionally, a
Crossref field to fall back to. Values are fetched from the publisher link
(and Crossref) with plain HTTP — no SerpAPI quota — during backfills and future
syncs, and stored per-publication in ``publications.custom_fields`` (JSON).

Where the exact meta-tag name is unclear, the local LLM can *suggest* likely
source keys, which the admin verifies before saving (nothing is fetched until
the column is created).
"""
from __future__ import annotations

import json
import logging
import re
import time

import httpx
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.publications.models import Publication, PublicationCustomColumn

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (compatible; ECE-Portal-CustomColumns/1.0; +https://ece.iiitd.ac.in)"
)

# Crossref fields that are safe to surface as scalar text.
_CROSSREF_FIELDS = {
    "issn": ("ISSN",),
    "isbn": ("ISBN",),
    "doi": ("DOI",),
    "volume": ("volume",),
    "issue": ("issue",),
    "pages": ("page",),
    "publisher": ("publisher",),
    "container": ("container-title",),
}


def slugify_key(label: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", (label or "").strip().lower()).strip("_")
    return key[:64] or "column"


# --- CRUD -------------------------------------------------------------------

def list_columns(db: Session, *, enabled_only: bool = False) -> list[PublicationCustomColumn]:
    stmt = select(PublicationCustomColumn).order_by(PublicationCustomColumn.label.asc())
    if enabled_only:
        stmt = stmt.where(PublicationCustomColumn.enabled.is_(True))
    return list(db.scalars(stmt).all())


def create_column(
    db: Session,
    *,
    label: str,
    description: str | None = None,
    source_keys: str | None = None,
    crossref_field: str | None = None,
    use_llm: bool = False,
) -> PublicationCustomColumn:
    label = (label or "").strip()
    if not label:
        raise ValueError("Column label is required")
    key = slugify_key(label)
    if db.scalar(select(PublicationCustomColumn).where(PublicationCustomColumn.key == key)):
        raise ValueError(f"A column with key '{key}' already exists")
    crossref = (crossref_field or "").strip().lower() or None
    if crossref and crossref not in _CROSSREF_FIELDS:
        raise ValueError(
            "crossref_field must be one of: " + ", ".join(sorted(_CROSSREF_FIELDS))
        )
    col = PublicationCustomColumn(
        key=key,
        label=label,
        description=(description or "").strip() or None,
        source_keys=(source_keys or "").strip() or None,
        crossref_field=crossref,
        use_llm=bool(use_llm),
        enabled=True,
    )
    db.add(col)
    db.commit()
    db.refresh(col)
    return col


def update_column(db: Session, column_id: int, **fields) -> PublicationCustomColumn | None:
    col = db.get(PublicationCustomColumn, column_id)
    if col is None:
        return None
    for name in ("label", "description", "source_keys", "crossref_field", "use_llm", "enabled"):
        if name in fields and fields[name] is not None:
            setattr(col, name, fields[name])
    db.commit()
    db.refresh(col)
    return col


def delete_column(db: Session, column_id: int) -> bool:
    col = db.get(PublicationCustomColumn, column_id)
    if col is None:
        return False
    db.delete(col)
    db.commit()
    return True


# --- custom_fields helpers --------------------------------------------------

def get_custom_fields(pub: Publication) -> dict[str, str]:
    if not pub.custom_fields:
        return {}
    try:
        data = json.loads(pub.custom_fields)
        return {str(k): ("" if v is None else str(v)) for k, v in data.items()} if isinstance(data, dict) else {}
    except (ValueError, TypeError):
        return {}


def set_custom_field(pub: Publication, key: str, value: str) -> None:
    data = get_custom_fields(pub)
    data[key] = value
    pub.custom_fields = json.dumps(data, ensure_ascii=False)


def set_custom_fields(pub: Publication, values: dict[str, str]) -> None:
    cleaned = {str(k): ("" if v is None else str(v)) for k, v in (values or {}).items()}
    pub.custom_fields = json.dumps(cleaned, ensure_ascii=False) if cleaned else None


# --- value resolution -------------------------------------------------------

def _meta_re(name: str) -> re.Pattern[str]:
    return re.compile(
        rf'<meta[^>]+(?:name|property)=["\']{re.escape(name)}["\'][^>]*?content=["\']([^"\']+)["\']'
        rf'|<meta[^>]+content=["\']([^"\']+)["\'][^>]*?(?:name|property)=["\']{re.escape(name)}["\']',
        re.IGNORECASE,
    )


def _extract_meta(html: str, keys: list[str]) -> str | None:
    for key in keys:
        m = _meta_re(key).search(html)
        if m:
            value = (m.group(1) or m.group(2) or "").strip()
            if value:
                return value
    return None


def _from_publisher_page(client: httpx.Client, url: str, keys: list[str]) -> str | None:
    try:
        resp = client.get(url, follow_redirects=True, timeout=15.0)
        if resp.status_code != 200 or not resp.text:
            return None
        return _extract_meta(resp.text, keys)
    except Exception as exc:  # network/parse failures are expected and non-fatal
        logger.debug("Custom column fetch failed for %s: %s", url, exc)
        return None


def _from_crossref(client: httpx.Client, title: str, crossref_field: str) -> str | None:
    if not title.strip():
        return None
    fields = _CROSSREF_FIELDS.get(crossref_field)
    if not fields:
        return None
    try:
        resp = client.get(
            "https://api.crossref.org/works",
            params={"query.bibliographic": title, "rows": 1},
            timeout=15.0,
        )
        if resp.status_code != 200:
            return None
        items = resp.json().get("message", {}).get("items", [])
        if not items:
            return None
        item = items[0]
        returned = (item.get("title") or [""])[0].strip().lower()
        if returned and returned[:40] != title.strip().lower()[:40]:
            return None
        for field in fields:
            value = item.get(field)
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value if v)
            if value:
                return str(value).strip()
    except Exception as exc:
        logger.debug("Crossref custom lookup failed for %r: %s", title[:60], exc)
    return None


def resolve_column_value(
    pub: Publication, column: PublicationCustomColumn, *, client: httpx.Client
) -> str | None:
    """Best-effort fetch of a single custom column value for one publication."""
    keys = [k.strip() for k in (column.source_keys or "").split(",") if k.strip()]
    if keys:
        for url in (pub.link, pub.pdf_url):
            if not url:
                continue
            value = _from_publisher_page(client, url, keys)
            if value:
                return value
    if column.crossref_field:
        value = _from_crossref(client, pub.title or "", column.crossref_field)
        if value:
            return value
    return None


# --- backfill ---------------------------------------------------------------

def _candidates_missing(db: Session, key: str, limit: int | None) -> list[Publication]:
    stmt = (
        select(Publication)
        .where(Publication.is_patent.is_(False))
        .where(or_(Publication.link.is_not(None), Publication.pdf_url.is_not(None), Publication.title.is_not(None)))
        .order_by(Publication.id.asc())
    )
    rows: list[Publication] = []
    for pub in db.scalars(stmt).all():
        if get_custom_fields(pub).get(key):
            continue
        rows.append(pub)
        if limit is not None and len(rows) >= limit:
            break
    return rows


def backfill_custom_columns(
    *, column_ids: list[int] | None = None, limit: int | None = None, delay_seconds: float = 0.5
) -> dict:
    """Fill missing custom-column values for existing publications from links/Crossref.

    Safe to run repeatedly; only fills values that are currently empty. Returns a
    per-column summary with checked/updated/error counts.
    """
    summary: dict[str, dict] = {}
    db = SessionLocal()
    try:
        columns = list_columns(db, enabled_only=True)
        if column_ids:
            columns = [c for c in columns if c.id in set(column_ids)]
        if not columns:
            return {"columns": {}, "message": "No enabled custom columns to backfill."}

        with httpx.Client(headers={"User-Agent": _USER_AGENT}) as client:
            for column in columns:
                checked = updated = errors = 0
                for pub in _candidates_missing(db, column.key, limit):
                    checked += 1
                    try:
                        value = resolve_column_value(pub, column, client=client)
                        if value:
                            set_custom_field(pub, column.key, value)
                            db.commit()
                            updated += 1
                    except Exception as exc:  # keep going on individual failures
                        db.rollback()
                        errors += 1
                        logger.warning("Custom column '%s' failed for pub %s: %s", column.key, pub.id, exc)
                    if delay_seconds > 0:
                        time.sleep(delay_seconds)
                summary[column.key] = {"label": column.label, "checked": checked, "updated": updated, "errors": errors}
    finally:
        db.close()
    logger.info("Custom column backfill complete: %s", summary)
    return {"columns": summary}


def run_custom_backfill_background(column_ids: list[int] | None = None, limit: int | None = None) -> None:
    backfill_custom_columns(column_ids=column_ids, limit=limit)


def fill_custom_columns_for_publications(
    db: Session, publications: list[Publication], *, client: httpx.Client
) -> None:
    """Populate custom columns for freshly-synced publications (best-effort)."""
    from app.publications.services.publication_service import get_manual_overrides

    columns = list_columns(db, enabled_only=True)
    if not columns:
        return
    for pub in publications:
        if "custom_fields" in set(get_manual_overrides(pub)):
            continue
        existing = get_custom_fields(pub)
        for column in columns:
            if existing.get(column.key):
                continue
            try:
                value = resolve_column_value(pub, column, client=client)
                if value:
                    set_custom_field(pub, column.key, value)
            except Exception as exc:
                logger.debug("Custom column '%s' fill skipped for pub %s: %s", column.key, pub.id, exc)


# --- LLM disambiguation (suggest, then admin verifies) ----------------------

async def suggest_column_sources(label: str, description: str | None = None) -> dict:
    """Ask the local LLM which meta-tag names / Crossref field likely hold the data.

    Returns a suggestion for the admin to review — it does NOT create the column
    or fetch anything.
    """
    guess: dict = {"label": label, "source_keys": "", "crossref_field": None, "note": ""}
    known_crossref = ", ".join(sorted(_CROSSREF_FIELDS))
    prompt = (
        "You help configure a scholarly-metadata scraper. Given a desired data field, "
        "list the HTML <meta> tag names that academic publishers (IEEE, Springer, "
        "ScienceDirect, ACM, MDPI, Wiley) commonly use for it, and the best matching "
        f"Crossref field from this list or 'none': {known_crossref}.\n"
        f"Desired field label: {label}\n"
        f"Extra context: {description or 'none'}\n"
        "Respond in exactly this format:\n"
        "meta: <comma-separated meta tag names>\n"
        "crossref: <one field or none>"
    )
    try:
        from app.llm.services.llm_dispatch import generate_text

        text = await generate_text(prompt, provider="local", temperature=0.0, max_tokens=200)
    except Exception as exc:
        guess["note"] = f"LLM unavailable ({exc}). Enter the meta tag name(s) manually."
        return guess

    for line in (text or "").splitlines():
        low = line.strip().lower()
        if low.startswith("meta:"):
            guess["source_keys"] = line.split(":", 1)[1].strip()
        elif low.startswith("crossref:"):
            val = line.split(":", 1)[1].strip().lower()
            if val in _CROSSREF_FIELDS:
                guess["crossref_field"] = val
    guess["note"] = "Review these suggested sources, edit if needed, then save the column."
    return guess
