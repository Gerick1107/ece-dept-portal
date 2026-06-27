"""One-time backfill of Winter 2023 CO/PO attainment into copo_run_analytics_snapshots.

Old-semester CO/PO attainment was recorded only as final CO and PO/PSO numbers in
``data/assets/Winter2023.csv`` (no raw marks / assessment IDs available). This script
parses that file and inserts analytics snapshots in the same JSON shape the portal
produces for live runs, so the historical data shows up in CO-PO analytics.

Usage (from backend/ with the venv active):
    python scripts/backfill_winter2023_copo.py            # dry run, prints what it will insert
    python scripts/backfill_winter2023_copo.py --commit   # write to the database

Re-running with --commit is idempotent: rows are matched/replaced by public_id.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from app.config import get_settings
from app.copo.engine.legacy_engine import extract_course_co_po_mapping, extract_course_co_po_mapping_pg
from app.copo.services.mapping_service import course_title_matches, extract_course_names
from app.courses.services.course_service import course_display_label, list_courses
from app.database.session import SessionLocal
from app.database.models.copo_analytics import CopoRunAnalyticsSnapshot

CSV_PATH = BACKEND_ROOT.parent / "data" / "assets" / "Winter2023.csv"

SEMESTER_LABEL = "Winter 2023"
RUN_CREATED_AT = datetime(2023, 5, 1)
EVALUATION_TYPE = "final_consolidated"
TARGET_VALUE = 50

PO_ORDER = [f"PO{i}" for i in range(1, 13)] + ["PSO1", "PSO2", "PSO3"]

_CODE_RE = re.compile(r"^(ECE|CSE|ENG|CS|EVE|CSER)-?[\d/]+", re.IGNORECASE)

_CO_RE = re.compile(r"^C[O0]\s*0*(\d+)$", re.IGNORECASE)
_PO_RE = re.compile(r"^(PSO|PO)\s*0*(\d+)$", re.IGNORECASE)


def _clean(cell: str | None) -> str:
    return (cell or "").strip()


def _is_number(cell: str) -> bool:
    try:
        float(cell)
        return True
    except (TypeError, ValueError):
        return False


def _co_label(cell: str) -> str | None:
    m = _CO_RE.match(_clean(cell))
    return f"CO{int(m.group(1))}" if m else None


def _po_label(cell: str) -> str | None:
    m = _PO_RE.match(_clean(cell))
    if not m:
        return None
    return f"{m.group(1).upper()}{int(m.group(2))}"


def _row_labels(row: list[str], kind: str) -> dict[int, str]:
    """Return {column_index: label} for CO or PO label cells in this row."""
    out: dict[int, str] = {}
    for idx, cell in enumerate(row):
        label = _co_label(cell) if kind == "co" else _po_label(cell)
        if label:
            out[idx] = label
    return out


def _find_value_row(rows: list[list[str]], header_idx: int, cols: list[int]) -> list[str] | None:
    for r in rows[header_idx + 1:]:
        if any(_is_number(r[c]) for c in cols if c < len(r)):
            return r
    return None


def _programme_to_scope(programme: str) -> str:
    p = programme.upper().replace(" ", "")
    if p == "UG/PG":
        return "Programmes: UG, PG"
    if p == "PG":
        return "Programmes: PG"
    if p == "UG":
        return "Programmes: UG"
    return f"Programmes: {programme}" if programme else "Programmes: UG"


def _normalize_code(code: str) -> str:
    return re.sub(r"\s+", "", code.upper())


def _course_code_from_text(text: str) -> str:
    match = _CODE_RE.match(text.strip())
    return match.group(0).upper() if match else text.split()[0].upper()


def _course_numbers_match(code_a: str, code_b: str) -> bool:
    nums_a = re.findall(r"\d+", _normalize_code(code_a))
    nums_b = re.findall(r"\d+", _normalize_code(code_b))
    return bool(nums_a and nums_a == nums_b)


def _resolve_canonical_title(db, code: str, fallback_name: str) -> tuple[str, bool]:
    """Match generator/DB course list and mapping sheet labels."""
    courses = list_courses(db)
    code_norm = _normalize_code(code)
    for course in courses:
        db_code = _normalize_code(course.course_code)
        if db_code == code_norm or code_norm in db_code or db_code in code_norm:
            return course_display_label(course), True
        if _course_numbers_match(code, course.course_code):
            return course_display_label(course), True

    settings = get_settings()
    patterns = [code, f"{code}: {fallback_name}"]
    for mapping_path in (settings.resolved_mapping_path, settings.resolved_pg_mapping_path):
        for label in extract_course_names(mapping_path):
            for pattern in patterns:
                if course_title_matches(pattern, label):
                    return label, True

    return f"{code}: {fallback_name}", False


def _infer_programme(programme: str, po_attainment: dict[str, float]) -> str:
    p = programme.upper().replace(" ", "")
    if p == "UG/PG":
        po_count = sum(1 for k in po_attainment if k.upper().startswith("PO"))
        return "PG" if po_count <= 4 else "UG"
    if p in ("UG", "PG"):
        return p
    po_count = sum(1 for k in po_attainment if k.upper().startswith("PO"))
    if po_count and po_count <= 4:
        return "PG"
    return "UG"


def _load_co_po_mapping(course_title: str, programme: str) -> dict[str, dict[str, float]]:
    settings = get_settings()
    try:
        if programme == "PG":
            mapping_df = extract_course_co_po_mapping_pg(settings.resolved_pg_mapping_path, course_title)
        else:
            mapping_df = extract_course_co_po_mapping(settings.resolved_mapping_path, course_title)
    except Exception:
        return {}
    return {
        str(co): {str(po): float(mapping_df.loc[co, po]) for po in mapping_df.columns}
        for co in mapping_df.index
    }


def parse_csv(path: Path, db) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        raw = [list(map(_clean, row)) for row in csv.reader(fh)]
    width = max(len(r) for r in raw)
    raw = [r + [""] * (width - len(r)) for r in raw]

    # Split into per-course blocks. A course starts when col0 is an integer index
    # and col1 holds a code + name.
    starts: list[int] = []
    for i, row in enumerate(raw):
        if row[0].isdigit() and row[1] and not _co_label(row[1]) and not _po_label(row[1]):
            starts.append(i)
    starts.append(len(raw))

    evaluations: list[dict] = []
    for s in range(len(starts) - 1):
        block = raw[starts[s]:starts[s + 1]]
        idx_num = int(block[0][0])
        code_name = block[0][1]
        code = _course_code_from_text(code_name)
        name = code_name[len(code):].strip().strip(":").strip()
        canonical_title, matched = _resolve_canonical_title(db, code, name)

        # Locate CO header rows and PO header rows within the block.
        co_headers = [(i, _row_labels(row, "co")) for i, row in enumerate(block) if len(_row_labels(row, "co")) >= 2]
        po_headers = [(i, _row_labels(row, "po")) for i, row in enumerate(block) if len(_row_labels(row, "po")) >= 2]

        # Pair CO and PO blocks in order. Course 7 has two (PG, then UG).
        pair_count = min(len(co_headers), len(po_headers))
        for k in range(pair_count):
            co_hidx, co_cols = co_headers[k]
            po_hidx, po_cols = po_headers[k]

            co_value_row = _find_value_row(block, co_hidx, list(co_cols))
            po_value_row = _find_value_row(block, po_hidx, list(po_cols))
            if co_value_row is None or po_value_row is None:
                continue

            programme = block[co_hidx][2] or co_value_row[2]
            programme = _clean(programme)
            # The PO value row of course 9 carries a note in col2; ignore notes.
            if programme.startswith("(") or _is_number(programme):
                programme = co_value_row[2] if not _is_number(co_value_row[2]) else ""

            co_attainment: dict[str, float] = {}
            for col, label in sorted(co_cols.items()):
                if col < len(co_value_row) and _is_number(co_value_row[col]):
                    co_attainment[label] = round(float(co_value_row[col]), 6)

            po_attainment: dict[str, float] = {}
            for col, label in sorted(po_cols.items(), key=lambda kv: PO_ORDER.index(kv[1]) if kv[1] in PO_ORDER else 99):
                if col < len(po_value_row) and _is_number(po_value_row[col]):
                    po_attainment[label] = round(float(po_value_row[col]), 6)

            if not co_attainment and not po_attainment:
                continue

            programme_label = _infer_programme(programme, po_attainment)
            co_po_mapping = _load_co_po_mapping(canonical_title, programme_label)
            suffix = f"_{programme_label.lower()}" if pair_count > 1 else ""
            public_id = f"backfill_w2023_{idx_num:02d}{suffix}"

            evaluations.append(
                {
                    "public_id": public_id,
                    "course_code": code,
                    "matched": matched,
                    "course_title": canonical_title,
                    "scope_summary": _programme_to_scope(programme_label),
                    "programme_label": programme_label,
                    "co_attainment": co_attainment,
                    "po_attainment": po_attainment,
                    "co_po_mapping": co_po_mapping,
                }
            )
    return evaluations


def build_result_summary(ev: dict) -> dict:
    unique_cos = sorted(ev["co_attainment"].keys(), key=lambda c: int(re.findall(r"\d+", c)[0]))
    co_po_mapping = ev.get("co_po_mapping") or {}
    intermediate = {
        "unique_COs": unique_cos,
        "co_warnings": [],
        "CO_stats": {"pct_above": ev["co_attainment"]},
        "CO_PO_mapping": co_po_mapping,
        "po_pso_attainment": ev["po_attainment"],
        "final_po_pso_attainment": ev["po_attainment"],
        "assessment_ids": [],
        "programme_label": ev.get("programme_label"),
        "backfill_note": "Historical Winter 2023 data; final CO/PO values only (no raw marks).",
    }
    return {
        "unique_COs": unique_cos,
        "co_warnings": [],
        "course_title": ev["course_title"],
        "scope_summary": ev["scope_summary"],
        "semester_label": SEMESTER_LABEL,
        "section_label": None,
        "programme_label": ev.get("programme_label"),
        "target_value": TARGET_VALUE,
        "intermediate": intermediate,
        "is_backfill": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true", help="write to the database")
    ap.add_argument("--csv", default=str(CSV_PATH))
    args = ap.parse_args()

    path = Path(args.csv)
    if not path.exists():
        print(f"CSV not found: {path}")
        return 1

    db = SessionLocal()
    try:
        evaluations = parse_csv(path, db)
    finally:
        db.close()

    print(f"Parsed {len(evaluations)} evaluation block(s) from {path.name}\n")
    for ev in evaluations:
        flag = "MATCHED" if ev["matched"] else "NEW    "
        mapping_flag = "mapping OK" if ev.get("co_po_mapping") else "no mapping"
        print(f"[{flag}] {ev['public_id']}  ->  {ev['course_title']}")
        print(f"          code={ev['course_code']}  scope={ev['scope_summary']}  {mapping_flag}")
        print(f"          CO: {ev['co_attainment']}")
        print(f"          PO: {ev['po_attainment']}")
        print()

    if not args.commit:
        print("Dry run only. Re-run with --commit to write these snapshots.")
        return 0

    db = SessionLocal()
    inserted = updated = 0
    try:
        for ev in evaluations:
            result_summary = build_result_summary(ev)
            existing = db.scalar(
                select(CopoRunAnalyticsSnapshot).where(
                    CopoRunAnalyticsSnapshot.public_id == ev["public_id"]
                )
            )
            if existing:
                existing.course_title = ev["course_title"]
                existing.evaluation_type = EVALUATION_TYPE
                existing.scope_summary = ev["scope_summary"]
                existing.semester_label = SEMESTER_LABEL
                existing.section_label = None
                existing.result_summary = result_summary
                existing.run_created_at = RUN_CREATED_AT
                updated += 1
            else:
                db.add(
                    CopoRunAnalyticsSnapshot(
                        public_id=ev["public_id"],
                        user_id=None,
                        course_title=ev["course_title"],
                        evaluation_type=EVALUATION_TYPE,
                        scope_summary=ev["scope_summary"],
                        semester_label=SEMESTER_LABEL,
                        section_label=None,
                        result_summary=result_summary,
                        run_created_at=RUN_CREATED_AT,
                    )
                )
                inserted += 1
        db.commit()
        print(f"Committed. inserted={inserted}, updated={updated}")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
