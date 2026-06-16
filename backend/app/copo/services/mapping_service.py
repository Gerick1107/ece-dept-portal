import os
import re

import pandas as pd

from app.config import get_settings

settings = get_settings()

_COURSE_CODE_RE = re.compile(r"(?:ECE|ENG|CSE|CS|EVE|CSER)-?[\d/]+", re.IGNORECASE)


def _normalize_course_code(code: str) -> str:
    """ECE-573 and ECE573 compare equal."""
    compact = re.sub(r"\s+", "", str(code).lower())
    return re.sub(r"^(ece|eng|cse|cs|eve|cser)-", r"\1", compact)


def _course_codes_in_text(text: str) -> list[str]:
    return [_normalize_course_code(m.group(0)) for m in _COURSE_CODE_RE.finditer(str(text))]

SHEET_PREFERENCE = [
    "Course outcome mapping UG",
    "CO mapping - PG",
    "Course mapping UG",
    "Course mapping PG",
]


def normalize_course_text(value: str) -> str:
    """Collapse spacing/punctuation variants from DB labels vs mapping sheet rows."""
    text = re.sub(r"\s+", " ", str(value).strip().lower())
    text = re.sub(r":\s*", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def course_title_matches(pattern: str, candidate: str) -> bool:
    """
  Match a selected course label to a mapping-sheet row.

  Handles DB labels like ``ECE-366/566: (NEID…)`` vs sheet rows
  ``ECE-366/566 (NEID…)`` (no colon).
  """
    p = normalize_course_text(pattern)
    c = normalize_course_text(candidate)
    if not p or not c:
        return False
    if p == c or p in c or c in p:
        return True
    pattern_codes = _course_codes_in_text(pattern)
    candidate_codes = _course_codes_in_text(candidate)
    if pattern_codes and candidate_codes:
        for pc in pattern_codes:
            for cc in candidate_codes:
                if pc == cc or pc in cc or cc in pc:
                    return True
    return False


def extract_course_names(mapping_path: str) -> list[str]:
    courses: list[str] = []
    try:
        xl = pd.ExcelFile(mapping_path)
        for sheet in SHEET_PREFERENCE:
            if sheet not in xl.sheet_names:
                continue
            df = pd.read_excel(mapping_path, sheet_name=sheet)
            if df.shape[1] < 16:
                continue
            first_col = df.columns[0]
            for raw in df[first_col]:
                if pd.isna(raw):
                    continue
                val = str(raw).strip()
                if not val or val.lower() == "nan":
                    continue
                if re.match(r"^CO\d+", val, re.IGNORECASE):
                    continue
                if re.match(r"^(PO|PSO)\d*$", val, re.IGNORECASE):
                    continue
                if len(val) > 3:
                    courses.append(val)
            if courses:
                break
    except Exception:
        pass
    return courses


def extract_cos_for_course(mapping_path: str, course_title: str) -> list[str]:
    try:
        xl = pd.ExcelFile(mapping_path)
        for sheet in SHEET_PREFERENCE:
            if sheet not in xl.sheet_names:
                continue
            df = pd.read_excel(mapping_path, sheet_name=sheet)
            if df.shape[1] < 16:
                continue
            first_col = df.columns[0]
            col0 = df[first_col]
            hits = [
                i
                for i, v in enumerate(col0.values)
                if isinstance(v, str) and course_title_matches(course_title, v)
            ]
            if not hits:
                continue
            start = hits[0]
            co_labels: list[str] = []
            i = start + 1
            while i < len(df):
                raw = df.loc[i, first_col]
                if pd.isna(raw):
                    break
                v = str(raw).strip()
                if v.upper().startswith("CO") and re.match(r"^CO\d+", v, re.IGNORECASE):
                    co_labels.append(v)
                    i += 1
                    continue
                if v.lower() == "nan" or v == "" or re.match(r"^\s*ECE-\d+", v):
                    break
                break
            if co_labels:
                return co_labels
    except Exception:
        pass
    return []


def lookup_indirect_values(
    indirect_path: str | None, course_title: str, co_labels: list[str]
) -> dict[str, float]:
    path = indirect_path or settings.resolved_indirect_path
    values: dict[str, float] = {}
    if not os.path.exists(path):
        return values
    try:
        indirect_df = pd.read_excel(path)
        match_row = None
        for idx, val in indirect_df.iloc[:, 0].items():
            if isinstance(val, str) and course_title_matches(course_title, val):
                match_row = idx
                break
        if match_row is not None:
            for co in co_labels:
                col_name = None
                if co in indirect_df.columns:
                    col_name = co
                else:
                    m = re.search(r"(\d+)", co)
                    if m:
                        co_num = m.group(1)
                        alt1 = f"C{co_num.zfill(2)}"
                        alt2 = f"C{int(co_num)}"
                        if alt1 in indirect_df.columns:
                            col_name = alt1
                        elif alt2 in indirect_df.columns:
                            col_name = alt2
                if col_name:
                    val = indirect_df.loc[match_row, col_name]
                    if pd.notna(val):
                        numeric_val = float(val)
                        if 0 <= numeric_val <= 1:
                            numeric_val *= 100.0
                        values[co] = numeric_val
    except Exception:
        pass
    return values


def resolve_mapping_path(
    use_default: bool,
    custom_path: str | None,
    *,
    mapping_type: str = "UG",
) -> str:
    if use_default or not custom_path:
        profile = str(mapping_type or "UG").upper()
        if profile == "PG":
            return settings.resolved_pg_mapping_path
        return settings.resolved_mapping_path
    return custom_path
