import os
import re

import pandas as pd

from app.config import get_settings

settings = get_settings()

SHEET_PREFERENCE = [
    "Course outcome mapping UG",
    "CO mapping - PG",
    "Course mapping UG",
    "Course mapping PG",
]


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
                if isinstance(v, str) and course_title.lower() in v.lower()
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
            if isinstance(val, str) and course_title.lower() in val.lower():
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


def resolve_mapping_path(use_default: bool, custom_path: str | None) -> str:
    if use_default or not custom_path:
        return settings.resolved_mapping_path
    return custom_path
