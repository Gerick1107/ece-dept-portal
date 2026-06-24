"""Resolve raw faculty names from contribution CSVs/forms to faculty.id."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.publications.models.entities import Faculty

logger = logging.getLogger(__name__)

_PREFIX_RE = re.compile(
    r"^(?:dr|prof|mr|ms|mrs|prof\.?\s*\(ms\)|prof\.?\s*\(mr\))\.?\s*",
    re.IGNORECASE,
)
_PUNCT_RE = re.compile(r"[.,']")

# Tunable matching config — aliases map raw spellings to faculty.id
FACULTY_MATCH_CONFIG = {
    "similarity_threshold": 0.90,
    "last_name_threshold": 0.85,
    "known_aliases": {
        "a v subramanmyam": 1,
        "a v subramanyam": 1,
        "subramanyam a v": 1,
        "vivek bohara": 24,
        "vivek ashok bohara": 24,
        "sumit darak": 23,
        "sumit j darak": 23,
        "sanjit kaul": 15,
        "sanjit krishnan kaul": 15,
        "chanekar prasad vilas": 7,
        "prasad vilas chanekar": 7,
    },
}


@dataclass(frozen=True)
class FacultyResolveResult:
    faculty_id: int
    matched_name: str
    confidence: Literal["exact", "token", "fuzzy", "alias"]
    raw_name: str


@dataclass(frozen=True)
class FacultyResolveFailure:
    raw_name: str
    reason: Literal["not_found", "ambiguous"]


def _normalize_name(name: str) -> str:
    cleaned = name.strip().lower()
    while True:
        match = _PREFIX_RE.match(cleaned)
        if not match:
            break
        cleaned = cleaned[match.end() :].strip()
    cleaned = _PUNCT_RE.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _tokens(name: str) -> list[str]:
    return [t for t in _normalize_name(name).split() if t]


def _is_initial(token: str) -> bool:
    return len(token.rstrip(".")) == 1


def _token_matches(a: str, b: str) -> bool:
    if a == b:
        return True
    a_core = a.rstrip(".")
    b_core = b.rstrip(".")
    if _is_initial(a_core) and b_core.startswith(a_core):
        return True
    if _is_initial(b_core) and a_core.startswith(b_core):
        return True
    return False


def _token_aware_match(incoming: list[str], candidate: list[str]) -> bool:
    if not incoming or not candidate:
        return False
    if incoming == candidate:
        return True
    short, long = (incoming, candidate) if len(incoming) <= len(candidate) else (candidate, incoming)
    if len(short) == 1:
        return len(long) == 1 and short[0] == long[0]
    if not _token_matches(short[0], long[0]):
        return False
    idx = 0
    for token in long:
        if _token_matches(short[idx], token):
            idx += 1
            if idx == len(short):
                return True
    return False


def _jaro_winkler(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _last_name(tokens: list[str]) -> str:
    return tokens[-1] if tokens else ""


def resolve_faculty_id(db: Session, raw_name: str) -> FacultyResolveResult | FacultyResolveFailure:
    raw = (raw_name or "").strip()
    if not raw:
        return FacultyResolveFailure(raw_name=raw, reason="not_found")

    normalized = _normalize_name(raw)
    alias_id = FACULTY_MATCH_CONFIG["known_aliases"].get(normalized)
    if alias_id:
        faculty = db.get(Faculty, alias_id)
        if faculty:
            return FacultyResolveResult(
                faculty_id=faculty.id,
                matched_name=faculty.name,
                confidence="alias",
                raw_name=raw,
            )

    faculty_rows = list(db.scalars(select(Faculty)).all())
    norm_map: dict[str, Faculty] = {}
    for f in faculty_rows:
        norm_map[_normalize_name(f.name)] = f

    if normalized in norm_map:
        f = norm_map[normalized]
        return FacultyResolveResult(faculty_id=f.id, matched_name=f.name, confidence="exact", raw_name=raw)

    incoming_tokens = _tokens(raw)
    token_matches: list[Faculty] = []
    for f in faculty_rows:
        if _token_aware_match(incoming_tokens, _tokens(f.name)):
            token_matches.append(f)
    if len(token_matches) == 1:
        f = token_matches[0]
        return FacultyResolveResult(faculty_id=f.id, matched_name=f.name, confidence="token", raw_name=raw)
    if len(token_matches) > 1:
        logger.warning("Ambiguous faculty name '%s' — token matches: %s", raw, [f.name for f in token_matches])
        return FacultyResolveFailure(raw_name=raw, reason="ambiguous")

    threshold = FACULTY_MATCH_CONFIG["similarity_threshold"]
    ln_threshold = FACULTY_MATCH_CONFIG["last_name_threshold"]
    incoming_ln = _last_name(incoming_tokens)
    best: tuple[float, Faculty] | None = None
    for f in faculty_rows:
        cand_norm = _normalize_name(f.name)
        score = _jaro_winkler(normalized, cand_norm)
        ln_score = _jaro_winkler(incoming_ln, _last_name(_tokens(f.name)))
        if score >= threshold and ln_score >= ln_threshold:
            if best is None or score > best[0]:
                best = (score, f)
    if best:
        f = best[1]
        return FacultyResolveResult(faculty_id=f.id, matched_name=f.name, confidence="fuzzy", raw_name=raw)

    logger.warning("Unmatched faculty name in contribution data: '%s'", raw)
    return FacultyResolveFailure(raw_name=raw, reason="not_found")


def resolve_faculty_id_required(db: Session, faculty_id: int) -> Faculty:
    faculty = db.get(Faculty, faculty_id)
    if not faculty:
        raise ValueError("Selected faculty not found")
    return faculty


def add_alias(raw_name: str, faculty_id: int) -> None:
    key = _normalize_name(raw_name)
    FACULTY_MATCH_CONFIG["known_aliases"][key] = faculty_id
