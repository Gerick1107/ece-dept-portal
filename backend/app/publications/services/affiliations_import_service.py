"""Parse Links.txt and persist faculty affiliations."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.publications.models.entities import Affiliation, Faculty, FacultyAffiliation
from app.utils.name_utils import names_match, strip_name_prefix

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_LINKS_PATH = _PROJECT_ROOT / "data" / "assets" / "Links.txt"

_AFFILIATION_LINE_RE = re.compile(
    r"^(.+?)\s*\((https?://[^)]+)\)\s*:\s*(.+)$",
    re.IGNORECASE,
)
_CATEGORY_MAP = {
    "research centres": "centre",
    "research groups": "group",
    "research labs": "lab",
}
_INVISIBLE_CHARS_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]+")


def _normalize_name(name: str) -> str:
    cleaned = _INVISIBLE_CHARS_RE.sub("", name.strip())
    return " ".join(strip_name_prefix(cleaned).split())


def _name_tokens(name: str) -> set[str]:
    return {t.lower() for t in _normalize_name(name).split() if t}


def _names_loosely_match(a: str, b: str) -> bool:
    if names_match(a, b):
        return True
    ta, tb = _name_tokens(a), _name_tokens(b)
    if not ta or not tb:
        return False
    if ta == tb:
        return True
    shorter, longer = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    return shorter.issubset(longer)


def _resolve_faculty_id(faculty_rows: list[Faculty], raw_name: str) -> int | None:
    target = _normalize_name(raw_name)
    for row in faculty_rows:
        if names_match(row.name, target):
            return row.id
    for row in faculty_rows:
        if _names_loosely_match(row.name, target):
            return row.id
    return None


def parse_links_file(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(f"Links file not found: {path}")

    category = "centre"
    parsed: list[dict] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = _INVISIBLE_CHARS_RE.sub("", raw_line).strip()
        if not line:
            continue
        lower = line.lower()
        if lower in _CATEGORY_MAP:
            category = _CATEGORY_MAP[lower]
            continue
        match = _AFFILIATION_LINE_RE.match(line)
        if not match:
            continue
        name, url, faculty_names = match.groups()
        members = [_normalize_name(n) for n in faculty_names.split(",") if n.strip()]
        parsed.append(
            {
                "name": name.strip(),
                "url": url.strip(),
                "category": category,
                "faculty_names": members,
            }
        )
    return parsed


def import_faculty_affiliations(db: Session, links_path: Path | None = None) -> dict:
    path = links_path or DEFAULT_LINKS_PATH
    entries = parse_links_file(path)
    faculty_rows = list(db.scalars(select(Faculty)).all())

    linked = 0
    removed_links = 0
    removed_affiliations = 0
    unmatched: list[str] = []
    file_affiliation_keys: set[tuple[str, str]] = set()

    for entry in entries:
        file_affiliation_keys.add((entry["name"], entry["url"]))
        affiliation = db.scalar(
            select(Affiliation).where(
                Affiliation.name == entry["name"],
                Affiliation.url == entry["url"],
            )
        )
        if affiliation is None:
            affiliation = Affiliation(
                name=entry["name"],
                url=entry["url"],
                category=entry["category"],
            )
            db.add(affiliation)
            db.flush()
        else:
            affiliation.category = entry["category"]

        desired_faculty_ids: set[int] = set()
        for member_name in entry["faculty_names"]:
            faculty_id = _resolve_faculty_id(faculty_rows, member_name)
            if faculty_id is None:
                unmatched.append(member_name)
                continue
            desired_faculty_ids.add(faculty_id)
            existing = db.scalar(
                select(FacultyAffiliation).where(
                    FacultyAffiliation.faculty_id == faculty_id,
                    FacultyAffiliation.affiliation_id == affiliation.id,
                )
            )
            if existing is None:
                db.add(FacultyAffiliation(faculty_id=faculty_id, affiliation_id=affiliation.id))
                linked += 1

        stale_links = db.scalars(
            select(FacultyAffiliation).where(FacultyAffiliation.affiliation_id == affiliation.id)
        ).all()
        for link in stale_links:
            if link.faculty_id not in desired_faculty_ids:
                db.delete(link)
                removed_links += 1

    for affiliation in db.scalars(select(Affiliation)).all():
        if (affiliation.name, affiliation.url) not in file_affiliation_keys:
            db.delete(affiliation)
            removed_affiliations += 1

    db.commit()
    if unmatched:
        logger.warning("Unmatched affiliation faculty names: %s", sorted(set(unmatched)))
    return {
        "affiliations_parsed": len(entries),
        "links_created": linked,
        "links_removed": removed_links,
        "affiliations_removed": removed_affiliations,
        "unmatched_names": sorted(set(unmatched)),
    }


def list_faculty_affiliations(db: Session, faculty_id: int) -> list[dict]:
    rows = db.execute(
        select(Affiliation)
        .join(FacultyAffiliation, FacultyAffiliation.affiliation_id == Affiliation.id)
        .where(FacultyAffiliation.faculty_id == faculty_id)
        .order_by(Affiliation.category, Affiliation.name)
    ).scalars().all()
    return [
        {
            "id": row.id,
            "name": row.name,
            "url": row.url,
            "category": row.category,
        }
        for row in rows
    ]
