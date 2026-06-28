"""Backfill historical CO/PO attainment into copo_run_analytics_snapshots.

Old semesters were recorded only as final CO and PO/PSO numbers in CSV files in
``data/assets`` (no raw marks / assessment IDs). This parses those CSVs and inserts
analytics snapshots in the same JSON shape the portal produces for live runs.

This is the generalized successor to ``backfill_winter2023_copo.py``. The older CSVs
(Monsoon 2022/2023, Winter 2024) are less regular:
  - some course rows have no leading index number,
  - PO headers sometimes read ``P10,P11,P12`` instead of ``PO10,PO11,PO12``,
  - a course's CO labels can sit on the row *above* an inline values row.
So the parser classifies rows (anchor / CO-label / PO-label / values) and aligns
values to labels by column, instead of assuming fixed offsets.

Programme (UG vs PG mapping) follows the rule: 12 PO + 3 PSO => UG mapped, 4 PO => PG.

Usage (from backend/ with the venv active):
    python scripts/backfill_legacy_copo.py             # dry run for all configured files
    python scripts/backfill_legacy_copo.py --commit    # write to the database
    python scripts/backfill_legacy_copo.py --only "Winter 2024" --commit

Re-running with --commit is idempotent: rows are matched/replaced by public_id.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from app.config import get_settings
from app.copo.engine.legacy_engine import extract_course_co_po_mapping, extract_course_co_po_mapping_pg
from app.copo.services.mapping_service import course_title_matches, extract_course_names
from app.courses.services.course_service import course_display_label, list_courses
from app.database.models.copo_analytics import CopoRunAnalyticsSnapshot
from app.database.session import SessionLocal

ASSETS = BACKEND_ROOT.parent / "data" / "assets"
EVALUATION_TYPE = "final_consolidated"
TARGET_VALUE = 50

# (filename, semester_label, public_id_tag, run_created_at)
FILES = [
    ("Monsoon 2022.csv", "Monsoon 2022", "m2022", datetime(2022, 11, 1)),
    ("Monsoon 2023.csv", "Monsoon 2023", "m2023", datetime(2023, 11, 1)),
    ("Winter2024.csv", "Winter 2024", "w2024", datetime(2024, 5, 1)),
]

PO_ORDER = [f"PO{i}" for i in range(1, 13)] + ["PSO1", "PSO2", "PSO3"]
# A primary code (ECE-366) optionally followed by slash-joined extra codes that may
# omit the department prefix (e.g. ECE-366/566, ECE-363/ECE-563/CSE-343/543).
_CODE_RE = re.compile(r"[A-Z]{2,4}-?\d{2,3}(?:/[A-Z]{0,4}-?\d{2,3})*")
_CO_RE = re.compile(r"^C[O0]\s*0*(\d+)$", re.IGNORECASE)
_PSO_RE = re.compile(r"^PSO\s*0*(\d+)$", re.IGNORECASE)
_PO_RE = re.compile(r"^P[O]?\s*0*(\d+)$", re.IGNORECASE)  # PO1, P10 (legacy) both -> PO


def _clean(cell) -> str:
    return str(cell).strip() if cell is not None else ""


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
    c = _clean(cell)
    m = _PSO_RE.match(c)
    if m:
        return f"PSO{int(m.group(1))}"
    m = _PO_RE.match(c)
    if m:
        return f"PO{int(m.group(1))}"
    return None


def _co_labels_in_row(row: list[str]) -> dict[int, str]:
    out: dict[int, str] = {}
    for idx, cell in enumerate(row):
        label = _co_label(cell)
        if label:
            out[idx] = label
    return out


def _po_labels_in_row(row: list[str]) -> dict[int, str]:
    out: dict[int, str] = {}
    for idx, cell in enumerate(row):
        label = _po_label(cell)
        if label:
            out[idx] = label
    return out


def _extract_code_name(col1: str) -> tuple[str, str]:
    m = _CODE_RE.match(col1.strip())
    if m:
        code = m.group(0).rstrip("/").upper()
        name = col1[m.end():].strip().strip(":").strip()
        return code, name or col1.strip()
    return "", col1.strip()


def _is_anchor(row: list[str]) -> bool:
    col0, col1 = row[0], row[1]
    if not col1 or _co_label(col1) or _po_label(col1):
        return False
    if _CODE_RE.match(col1.strip()):
        return True
    if col0.isdigit():
        return True
    return False


def _course_numbers(text: str) -> set[str]:
    return set(re.findall(r"\d{3}", text))


def _norm_name(text: str) -> str:
    """Lowercase course name with punctuation flattened to spaces.

    Parenthesis characters are dropped but the words inside are kept — some mapping
    labels have malformed/nested parens, so removing the *content* would erase the name.
    """
    s = text.lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _name_sim(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


_CODE_NUM_THRESHOLD = 0.45  # name sim required when course codes share a number
_NAME_ONLY_THRESHOLD = 0.85  # name sim required when no code is available to confirm


def _candidate_titles(db) -> list[str]:
    titles = [course_display_label(c) for c in list_courses(db)]
    settings = get_settings()
    for mapping_path in (settings.resolved_mapping_path, settings.resolved_pg_mapping_path):
        try:
            titles.extend(extract_course_names(mapping_path))
        except Exception:
            pass
    seen: set[str] = set()
    unique: list[str] = []
    for t in titles:
        key = t.strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(t)
    return unique


def _resolve_canonical_title(db, code: str, name: str, raw_title: str, candidates: list[str]) -> tuple[str, bool]:
    """Match to a current course only when code AND name agree (or name matches strongly).

    Course codes have been reused across years (e.g. ECE-340 was two different courses),
    so a shared code number alone is not enough — the names must also be similar.
    """
    legacy_nums = _course_numbers(raw_title)
    legacy_name = _norm_name(name or raw_title)

    best: tuple[float, str] | None = None
    for label in candidates:
        cand_code, cand_name = _extract_code_name(label)
        cand_nums = _course_numbers(label)
        sim = _name_sim(legacy_name, _norm_name(cand_name or label))
        shares_code = bool(legacy_nums & cand_nums)

        score: float | None = None
        if shares_code and sim >= _CODE_NUM_THRESHOLD:
            score = 1.0 + sim
        elif not legacy_nums and sim >= _NAME_ONLY_THRESHOLD:
            score = sim

        if score is not None and (best is None or score > best[0]):
            best = (score, label)

    if best:
        return best[1], True
    return (f"{code}: {name}" if code else (name or raw_title)), False


def _infer_programme(programme_token: str, po_attainment: dict[str, float]) -> str:
    po_count = sum(1 for k in po_attainment if k.upper().startswith("PO"))
    p = programme_token.upper().replace(" ", "")
    if p in ("UG", "PG") and po_count:
        # Trust the PO-count rule when it clearly disagrees (4 POs => PG mapped).
        if po_count <= 4:
            return "PG"
        if po_count >= 10:
            return "UG"
        return p
    if po_count and po_count <= 4:
        return "PG"
    return "UG"


def _scope_for(programme: str) -> str:
    return "Programmes: PG" if programme == "PG" else "Programmes: UG"


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


def _norm_rows(path: Path) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        raw = [[_clean(c) for c in row] for row in csv.reader(fh)]
    raw = [r for r in raw if any(r)]
    width = max((len(r) for r in raw), default=0)
    return [r + [""] * (width - len(r)) for r in raw]


def _find_values_after(rows: list[list[str]], label_idx: int, cols: list[int], lookahead: int = 4):
    for j in range(label_idx + 1, min(len(rows), label_idx + 1 + lookahead)):
        r = rows[j]
        if _co_labels_in_row(r) or _po_labels_in_row(r):
            return None
        if any(c < len(r) and _is_number(r[c]) for c in cols):
            return j, r
    return None


def _values_for(label_row: dict[int, str], value_row: list[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for col, label in label_row.items():
        if col < len(value_row) and _is_number(value_row[col]):
            out[label] = round(float(value_row[col]), 6)
    return out


def _programme_token(rows: list[list[str]], anchor_idx: int, value_idx: int) -> str:
    for idx in (value_idx, anchor_idx):
        if 0 <= idx < len(rows):
            tok = _clean(rows[idx][2]).upper().replace(" ", "")
            if tok in ("UG", "PG", "UG/PG"):
                return tok
    return ""


def parse_legacy_csv(path: Path, db, semester_label: str, tag: str) -> list[dict]:
    rows = _norm_rows(path)
    candidates = _candidate_titles(db)

    anchors = [i for i, r in enumerate(rows) if _is_anchor(r)]

    def anchor_for(row_idx: int) -> int | None:
        chosen = None
        for ai in anchors:
            if ai <= row_idx:
                chosen = ai
            else:
                break
        return chosen

    # Collect CO and PO (label_row, values) pairs across the file, keyed by anchor.
    co_pairs: dict[int, list[tuple[dict[int, str], list[str], int]]] = {}
    po_pairs: dict[int, list[tuple[dict[int, str], list[str], int]]] = {}

    for i, row in enumerate(rows):
        co_labels = _co_labels_in_row(row)
        po_labels = _po_labels_in_row(row)
        if len(co_labels) >= 2:
            found = _find_values_after(rows, i, list(co_labels))
            if found:
                vidx, vrow = found
                a = anchor_for(vidx)
                if a is not None:
                    co_pairs.setdefault(a, []).append((co_labels, vrow, vidx))
        if len(po_labels) >= 2:
            found = _find_values_after(rows, i, list(po_labels))
            if found:
                vidx, vrow = found
                a = anchor_for(vidx)
                if a is not None:
                    po_pairs.setdefault(a, []).append((po_labels, vrow, vidx))

    evaluations: list[dict] = []
    for seq, anchor_idx in enumerate(anchors, start=1):
        code, name = _extract_code_name(rows[anchor_idx][1])
        raw_title = rows[anchor_idx][1]
        canonical_title, matched = _resolve_canonical_title(db, code, name, raw_title, candidates)

        cos = sorted(co_pairs.get(anchor_idx, []), key=lambda t: t[2])
        pos = sorted(po_pairs.get(anchor_idx, []), key=lambda t: t[2])
        variant_count = max(len(cos), len(pos))
        if variant_count == 0:
            continue

        for k in range(variant_count):
            co_label_row, co_value_row, co_vidx = cos[k] if k < len(cos) else ({}, [], anchor_idx)
            po_label_row, po_value_row, _ = pos[k] if k < len(pos) else ({}, [], anchor_idx)

            co_attainment = _values_for(co_label_row, co_value_row) if co_label_row else {}
            po_attainment = _values_for(po_label_row, po_value_row) if po_label_row else {}
            if not co_attainment and not po_attainment:
                continue

            programme_token = _programme_token(rows, anchor_idx, co_vidx)
            programme = _infer_programme(programme_token, po_attainment)
            co_po_mapping = _load_co_po_mapping(canonical_title, programme)

            suffix = f"_{programme.lower()}" if variant_count > 1 else ""
            public_id = f"backfill_{tag}_{seq:02d}{suffix}"

            evaluations.append(
                {
                    "public_id": public_id,
                    "course_code": code or "(no code)",
                    "raw_title": raw_title,
                    "matched": matched,
                    "course_title": canonical_title,
                    "scope_summary": _scope_for(programme),
                    "programme_label": programme,
                    "co_attainment": co_attainment,
                    "po_attainment": po_attainment,
                    "co_po_mapping": co_po_mapping,
                    "semester_label": semester_label,
                }
            )
    return evaluations


def build_result_summary(ev: dict) -> dict:
    unique_cos = sorted(ev["co_attainment"].keys(), key=lambda c: int(re.findall(r"\d+", c)[0]))
    intermediate = {
        "unique_COs": unique_cos,
        "co_warnings": [],
        "CO_stats": {"pct_above": ev["co_attainment"]},
        "CO_PO_mapping": ev.get("co_po_mapping") or {},
        "po_pso_attainment": ev["po_attainment"],
        "final_po_pso_attainment": ev["po_attainment"],
        "assessment_ids": [],
        "programme_label": ev.get("programme_label"),
        "backfill_note": f"Historical {ev['semester_label']} data; final CO/PO values only (no raw marks).",
    }
    return {
        "unique_COs": unique_cos,
        "co_warnings": [],
        "course_title": ev["course_title"],
        "scope_summary": ev["scope_summary"],
        "semester_label": ev["semester_label"],
        "section_label": None,
        "programme_label": ev.get("programme_label"),
        "target_value": TARGET_VALUE,
        "intermediate": intermediate,
        "is_backfill": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true", help="write to the database")
    ap.add_argument("--only", default=None, help="process only this semester label (e.g. 'Winter 2024')")
    args = ap.parse_args()

    targets = [f for f in FILES if not args.only or f[1].lower() == args.only.lower()]
    if not targets:
        print(f"No configured file matches --only '{args.only}'. Known: {[f[1] for f in FILES]}")
        return 1

    db = SessionLocal()
    inserted = updated = 0
    try:
        for filename, semester_label, tag, run_created_at in targets:
            path = ASSETS / filename
            if not path.exists():
                print(f"SKIP (missing): {path}")
                continue

            evaluations = parse_legacy_csv(path, db, semester_label, tag)
            print(f"\n=== {semester_label}  ({filename}) — {len(evaluations)} evaluation block(s) ===")
            for ev in evaluations:
                flag = "MATCHED" if ev["matched"] else "NEW    "
                mapping_flag = "mapping OK" if ev.get("co_po_mapping") else "no mapping"
                print(f"[{flag}] {ev['public_id']}  ->  {ev['course_title']}  ({ev['programme_label']}, {mapping_flag})")
                print(f"          raw='{ev['raw_title']}'")
                print(f"          CO: {ev['co_attainment']}")
                print(f"          PO({sum(1 for k in ev['po_attainment'] if k.startswith('PO'))} PO): {ev['po_attainment']}")

            if not args.commit:
                continue

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
                    existing.semester_label = ev["semester_label"]
                    existing.section_label = None
                    existing.result_summary = result_summary
                    existing.run_created_at = run_created_at
                    updated += 1
                else:
                    db.add(
                        CopoRunAnalyticsSnapshot(
                            public_id=ev["public_id"],
                            user_id=None,
                            course_title=ev["course_title"],
                            evaluation_type=EVALUATION_TYPE,
                            scope_summary=ev["scope_summary"],
                            semester_label=ev["semester_label"],
                            section_label=None,
                            result_summary=result_summary,
                            run_created_at=run_created_at,
                        )
                    )
                    inserted += 1

        if args.commit:
            db.commit()
            print(f"\nCommitted. inserted={inserted}, updated={updated}")
        else:
            print("\nDry run only. Re-run with --commit to write these snapshots.")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
