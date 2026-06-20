"""
Normalize faculty marks workbooks to the layout expected by legacy_engine.

Handles:
- Sample / template layout (Semester-Year + Branch columns, multi-row headers)
- ADC-style grids (Branch + name columns before assessments)
- Standard files with only CO-row fixes (none → empty, Bonus_* → Bonus)
"""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

import pandas as pd

from app.config import get_settings

_BONUS_COL_RE = re.compile(r"^bonus", re.IGNORECASE)
_METADATA_INDEX = frozenset(
    {"CO", "CO TO BE ENTERED", "MAX_MARKS", "MAX MARKS", "MARKS", "MAX_MARKS_SCALED", "ROLL NO.", "ROLL NO", "BRANCH"}
)
_CO_LABELS = frozenset({"co", "co to be entered"})
_MAX_MARKS_LABELS = frozenset({"max_marks", "max marks", "maxmarks", "marks"})
_RESULT_LABELS = frozenset(
    {"result", "total_marks", "total_marks_100", "total_marks_aft", "total_marks_after_bonus", "final marks", "final_marks"}
)
_GRADE_LABELS = frozenset(
    {"grade_point", "grade point", "grade", "final grade", "final_grade", "numerical value", "numerical_grade"}
)


def is_co_empty(value) -> bool:
    if pd.isna(value):
        return True
    s = str(value).strip().lower()
    return s in ("", "nan", "none", "null", "n/a", "-", "—")


def is_bonus_column(name: str) -> bool:
    return bool(_BONUS_COL_RE.match(str(name).strip()))


def is_bonus_assessment_column(name: str) -> bool:
    """Bonus question columns (Bonus_Q6) and whole bonus components (Attendance_Bonus)."""
    n = str(name).strip().lower()
    if n in ("bonus", "branch"):
        return False
    if n.endswith("_bonus"):
        return True
    return n.startswith("bonus")


def _cell_str(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _normalize_label(value) -> str:
    return re.sub(r"\s+", " ", _cell_str(value).lower())


def _is_co_label(value) -> bool:
    return _normalize_label(value) in _CO_LABELS


def _is_max_marks_label(value) -> bool:
    return _normalize_label(value).replace(" ", "_") in _MAX_MARKS_LABELS or (
        "max" in _normalize_label(value) and "mark" in _normalize_label(value)
    )


def _is_result_label(value) -> bool:
    norm = _normalize_label(value).replace(" ", "_")
    return norm in _RESULT_LABELS or norm.startswith("total_marks")


def _is_grade_label(value) -> bool:
    norm = _normalize_label(value).replace(" ", "_")
    if norm in _GRADE_LABELS or norm.startswith("grade_point"):
        return True
    if norm.startswith("grade_letter") or norm in ("letter_grade", "gradeletter"):
        return True
    return "grade" in norm and "letter" in norm


def _is_grade_column_name(col_name: str) -> bool:
    norm = _normalize_label(col_name).replace(" ", "_")
    if _is_grade_label(col_name):
        return True
    if norm.startswith("grade_letter") or norm.startswith("grade_point"):
        return True
    return "grade" in norm and "letter" in norm


def _is_trailer_column(name: str) -> bool:
    if name == "Result":
        return True
    return _is_grade_column_name(name)


def _looks_like_roll_number(value) -> bool:
    roll = _cell_str(value)
    if not roll or roll.lower() in ("roll no.", "roll no", "branch", "nan", "s.no", "s.no."):
        return False
    upper = roll.upper()
    if upper in ("CO", "MAX_MARKS", "MAX MARKS", "RESULT", "GRADE_POINT", "GRADE_LETTER", "BONUS"):
        return False
    if re.match(r"^(MT|PhD|\d)", roll, re.IGNORECASE):
        return True
    # Alphanumeric student IDs (exchange / special programmes, e.g. SP26003)
    return bool(re.match(r"^[A-Za-z0-9][A-Za-z0-9\-]{2,15}$", roll))


def _find_co_metadata_cell(raw: pd.DataFrame, max_rows: int = 15) -> tuple[int, int] | None:
    for r in range(min(max_rows, len(raw))):
        for c in range(min(8, raw.shape[1])):
            if _is_co_label(raw.iloc[r, c]):
                return r, c
    return None


def _find_max_marks_cell(raw: pd.DataFrame, near_row: int | None = None, max_rows: int = 15) -> tuple[int, int] | None:
    search_rows = list(range(min(max_rows, len(raw))))
    if near_row is not None:
        search_rows = sorted({near_row - 1, near_row, near_row + 1, near_row + 2} | set(search_rows))
    for r in search_rows:
        if r < 0 or r >= len(raw):
            continue
        for c in range(min(8, raw.shape[1])):
            if _is_max_marks_label(raw.iloc[r, c]):
                return r, c
    return None


def _find_roll_column(raw: pd.DataFrame, max_rows: int = 15) -> int:
    for r in range(min(max_rows, len(raw))):
        for c in range(min(8, raw.shape[1])):
            if _normalize_label(raw.iloc[r, c]) in ("roll no.", "roll no"):
                return c
    return 1


def _find_data_start_row(raw: pd.DataFrame, after_row: int, roll_col: int) -> int:
    for r in range(after_row + 1, len(raw)):
        if _looks_like_roll_number(raw.iloc[r, roll_col]):
            return r
    return after_row + 1


def _find_first_assessment_col(raw: pd.DataFrame, header_rows: range, roll_col: int) -> int:
    meta_cols: set[int] = set()
    for r in header_rows:
        if r < 0 or r >= len(raw):
            continue
        for c in range(min(10, raw.shape[1])):
            label = _normalize_label(raw.iloc[r, c])
            if label in (
                "branch",
                "roll no.",
                "roll no",
                "name",
                "email id",
                "email",
                "s.no",
                "s.no.",
                "semester-year",
                "3xx/5xx",
            ) or _is_co_label(raw.iloc[r, c]) or _is_max_marks_label(raw.iloc[r, c]):
                meta_cols.add(c)
    if roll_col in meta_cols:
        meta_cols.add(roll_col)
    return (max(meta_cols) + 1) if meta_cols else max(roll_col + 1, 2)


def _is_sample_layout(raw: pd.DataFrame) -> bool:
    if raw.empty:
        return False
    top_left = _cell_str(raw.iloc[0, 0]).lower()
    if "semester" in top_left and "year" in top_left.replace("-", " "):
        return True
    if raw.shape[0] > 1 and raw.shape[1] > 1:
        c0 = _cell_str(raw.iloc[1, 0]).lower()
        c1 = _cell_str(raw.iloc[1, 1]).lower()
        if c0 == "branch" and "roll" in c1:
            return True
    if _find_co_metadata_cell(raw) and _find_max_marks_cell(raw):
        return True
    if raw.shape[1] > 2 and "roll" in _cell_str(raw.iloc[0, 0]).lower():
        if "semester" in _cell_str(raw.iloc[0, 1]).lower() or _find_co_metadata_cell(raw):
            return True
    for r in range(min(6, len(raw))):
        for c in range(min(4, raw.shape[1] - 1)):
            if _cell_str(raw.iloc[r, c]).lower() == "branch" and "roll" in _cell_str(raw.iloc[r, c + 1]).lower():
                return True
    return False


def _is_adc_branch_grid(raw: pd.DataFrame) -> bool:
    """ADC-style: CO row, then Max_Marks row with 'Branch' in column 1."""
    if raw.shape[0] < 5 or raw.shape[1] < 4:
        return False
    for r in range(min(8, len(raw))):
        if _cell_str(raw.iloc[r, 0]).upper() == "CO":
            if r + 1 < len(raw) and _cell_str(raw.iloc[r + 1, 1]).lower() == "branch":
                return True
    return False


def _find_row_label(raw: pd.DataFrame, label: str, col: int = 1, max_rows: int = 12) -> int | None:
    target = label.strip().lower()
    for r in range(min(max_rows, len(raw))):
        if _cell_str(raw.iloc[r, col]).lower() == target:
            return r
    return None


def _build_column_names(raw: pd.DataFrame, start_col: int) -> list[str]:
    """Build stable assessment column names from one or two header rows."""
    names: list[str] = []
    group_counts: dict[str, int] = {}
    last_group = ""
    for j in range(start_col, raw.shape[1]):
        g = _cell_str(raw.iloc[0, j]) if len(raw) > 0 else ""
        if g:
            last_group = g
        elif last_group:
            g = last_group
        s = _cell_str(raw.iloc[1, j]) if len(raw) > 1 else ""
        if s.lower() in ("-", "—"):
            s = ""
        base = s or g
        if not base or base.lower() in ("roll no.", "roll no", "branch", "name", "email id", "email"):
            names.append(f"_skip_{j}")
            continue
        if _is_result_label(base) or (len(raw) > 2 and _is_result_label(raw.iloc[2, j])):
            if "Result" not in names:
                names.append("Result")
            else:
                names.append(f"_skip_{j}")
            continue
        if _is_grade_label(base):
            label = _normalize_label(base).replace(" ", "_")
            if "letter" in label:
                name = "Grade_letter" if "Grade_letter" not in names else f"Grade_letter.{j}"
            elif "Grade_Point" not in names:
                name = "Grade_Point"
            else:
                name = f"Grade_Point.{j}"
            names.append(name)
            continue
        if g and s and s.lower() != "total" and not s.lower().startswith("bonus_q"):
            key = g
            group_counts[key] = group_counts.get(key, 0) + 1
            names.append(f"{g}.{group_counts[key]}")
        elif s.lower().startswith("bonus_q"):
            names.append(s)
        elif s.lower() == "total" and g:
            # Standalone component (only a Total sub-column, no Q1/Q2/…) → use group name.
            if group_counts.get(g, 0) == 0:
                names.append(g)
            else:
                key = f"{g}::total"
                if key not in group_counts:
                    group_counts[key] = 0
                    names.append(f"{g}.total")
                else:
                    group_counts[key] += 1
                    names.append(f"{g}.total{group_counts[key]}")
        else:
            key = base
            if key not in group_counts:
                group_counts[key] = 0
                names.append(base)
            else:
                group_counts[key] += 1
                names.append(f"{base}.{group_counts[key]}")
    return names


def _normalize_co_value(value) -> str:
    if is_co_empty(value):
        return ""
    return ",".join(part.strip() for part in str(value).split(",") if part.strip())


def _normalized_temp_dir() -> Path:
    """Ephemeral normalized workbooks — not mixed with faculty uploads."""
    settings = get_settings()
    dest_dir = Path(settings.upload_dir).parent / "temp" / "normalized"
    dest_dir.mkdir(parents=True, exist_ok=True)
    return dest_dir


def _write_workbook(df: pd.DataFrame, source_path: str) -> str:
    dest = _normalized_temp_dir() / f"normalized_{uuid.uuid4().hex}_{Path(source_path).name}"
    df.to_excel(dest, index=True)
    return str(dest)


def _grade_value_count(df: pd.DataFrame, col: str) -> int:
    metadata = {"CO", "Max_Marks", "Max_Marks_scaled", "Roll No.", "Roll No", "Branch"}
    count = 0
    for idx in df.index:
        if str(idx).strip() in metadata:
            continue
        val = df.loc[idx, col]
        if pd.isna(val):
            continue
        s = str(val).strip()
        if s and s.lower() not in ("nan", ""):
            count += 1
    return count


def _pick_grade_column(df: pd.DataFrame, candidates: list[str]) -> str:
    with_data = [c for c in candidates if _grade_value_count(df, c) > 0]
    pool = with_data or candidates
    metadata = {"CO", "Max_Marks", "Max_Marks_scaled", "Roll No.", "Roll No", "Branch"}

    def _student_samples(col: str) -> list[str]:
        sample: list[str] = []
        for idx in df.index:
            if str(idx).strip() in metadata:
                continue
            val = df.loc[idx, col]
            if pd.isna(val):
                continue
            s = str(val).strip()
            if s and s.lower() not in ("nan", ""):
                sample.append(s)
            if len(sample) >= 30:
                break
        return sample

    letter_cols: list[str] = []
    numeric_cols: list[str] = []
    for col in pool:
        samples = _student_samples(col)
        if any(re.match(r"^[A-F][+-]?$", s.upper()) for s in samples):
            letter_cols.append(col)
        elif any(re.match(r"^\d+$", s) for s in samples):
            numeric_cols.append(col)

    if letter_cols:
        return max(letter_cols, key=lambda c: _grade_value_count(df, c))
    if numeric_cols:
        return max(numeric_cols, key=lambda c: _grade_value_count(df, c))
    return max(pool, key=lambda c: _grade_value_count(df, c))


def _finalize_standard_columns(df: pd.DataFrame) -> pd.DataFrame:
    if "Result" not in df.columns:
        for col in list(df.columns):
            if _is_result_label(col) or _normalize_label(col).startswith("result"):
                df.rename(columns={col: "Result"}, inplace=True)
                break
        if "Result" not in df.columns:
            for col in list(df.columns):
                if _normalize_label(col).startswith("result."):
                    df.rename(columns={col: "Result"}, inplace=True)
                    break

    grade_candidates = [str(col) for col in df.columns if _is_grade_column_name(str(col))]
    if grade_candidates:
        best = _pick_grade_column(df, grade_candidates)
        for col in grade_candidates:
            if col != best and col in df.columns:
                df.drop(columns=[col], inplace=True)
        if best != "Grade_Point":
            df.rename(columns={best: "Grade_Point"}, inplace=True)
    return df


def _rename_metadata_index(df: pd.DataFrame) -> pd.DataFrame:
    rename_map: dict = {}
    for idx in df.index:
        label = str(idx).strip().upper()
        if label in ("CO TO BE ENTERED",):
            rename_map[idx] = "CO"
        elif label == "MARKS":
            rename_map[idx] = "Max_Marks"
        elif label == "MAX MARKS":
            rename_map[idx] = "Max_Marks"
    if rename_map:
        df.rename(index=rename_map, inplace=True)
    return df


def _build_assessment_table(
    raw: pd.DataFrame,
    *,
    co_row: int,
    max_row: int,
    roll_col: int,
    branch_col: int | None,
    start_col: int,
    col_names: list[str],
    data_start: int,
) -> tuple[list[str], list[int], list[tuple[str, dict]], dict, dict, list[str]] | None:
    assessment_cols: list[str] = []
    col_indices: list[int] = []
    for j, name in enumerate(col_names, start=start_col):
        if name.startswith("_skip_"):
            continue
        if _is_trailer_column(name):
            assessment_cols.append(name)
            col_indices.append(j)
            continue
        assessment_cols.append(name)
        col_indices.append(j)

    regular_cols = [
        c
        for c in assessment_cols
        if not is_bonus_column(c) and not is_bonus_assessment_column(c) and not _is_trailer_column(c)
    ]

    co_values: dict[str, str] = {}
    max_values: dict[str, float | str] = {}
    for name, j in zip(assessment_cols, col_indices):
        if _is_trailer_column(name):
            co_values[name] = ""
            max_values[name] = ""
            continue
        co_values[name] = _normalize_co_value(raw.iloc[co_row, j])
        max_val = raw.iloc[max_row, j]
        max_values[name] = "" if is_co_empty(max_val) else max_val

    rows: list[tuple[str, dict]] = []
    for r in range(data_start, len(raw)):
        roll = _cell_str(raw.iloc[r, roll_col])
        if not _looks_like_roll_number(roll):
            continue

        entry: dict = {}
        if branch_col is not None and branch_col >= 0:
            branch_path = _cell_str(raw.iloc[r, branch_col])
            entry["Branch"] = branch_path if branch_path and branch_path.lower() != "nan" else ""

        bonus_sum = 0.0
        has_bonus = False
        for name, j in zip(assessment_cols, col_indices):
            val = raw.iloc[r, j]
            if is_bonus_column(name) or is_bonus_assessment_column(name):
                try:
                    bonus_sum += float(val)
                    has_bonus = True
                except (TypeError, ValueError):
                    pass
            else:
                entry[name] = val
        if has_bonus:
            entry["Bonus"] = bonus_sum
        rows.append((roll, entry))

    if not rows:
        return None

    out_cols: list[str] = []
    if branch_col is not None and branch_col >= 0:
        out_cols.append("Branch")
    out_cols.extend(regular_cols)
    if any(is_bonus_column(c) or is_bonus_assessment_column(c) for c in assessment_cols):
        out_cols.append("Bonus")
    for req in [c for c in assessment_cols if _is_trailer_column(c)]:
        if req not in out_cols:
            out_cols.append(req)

    seen: set[str] = set()
    out_cols_unique: list[str] = []
    for c in out_cols:
        if c not in seen:
            seen.add(c)
            out_cols_unique.append(c)

    return out_cols_unique, col_indices, rows, co_values, max_values, assessment_cols


def _dataframe_from_assessment_table(
    out_cols: list[str],
    rows: list[tuple[str, dict]],
    co_values: dict[str, str],
    max_values: dict[str, float | str],
) -> pd.DataFrame:
    df = pd.DataFrame(index=["CO", "Max_Marks"] + [r for r, _ in rows], columns=out_cols)
    for name in out_cols:
        if name == "Branch":
            df.loc["CO", name] = ""
            df.loc["Max_Marks", name] = ""
            for roll, entry in rows:
                df.loc[roll, name] = entry.get("Branch", "")
        elif name == "Bonus":
            df.loc["CO", name] = ""
            df.loc["Max_Marks", name] = ""
            for roll, entry in rows:
                df.loc[roll, name] = entry.get("Bonus", 0)
        else:
            df.loc["CO", name] = co_values.get(name, "")
            df.loc["Max_Marks", name] = max_values.get(name, "")
            for roll, entry in rows:
                if name in entry:
                    df.loc[roll, name] = entry[name]
    return _finalize_standard_columns(df)


def _from_sample_layout(raw: pd.DataFrame, source_path: str) -> str:
    co_cell = _find_co_metadata_cell(raw)
    if co_cell is None:
        return source_path
    co_row, _meta_col = co_cell

    max_cell = _find_max_marks_cell(raw, near_row=co_row)
    if max_cell is None:
        return source_path
    max_row, _ = max_cell

    roll_col = _find_roll_column(raw)
    branch_col = None
    for c in range(roll_col):
        for r in range(min(4, len(raw))):
            if _normalize_label(raw.iloc[r, c]) == "branch":
                branch_col = c
                break
        if branch_col is not None:
            break
    if branch_col is None and roll_col > 0:
        branch_col = roll_col - 1
        for r in range(min(max_row + 1, len(raw))):
            if _is_co_label(raw.iloc[r, branch_col]) or _is_max_marks_label(raw.iloc[r, branch_col]):
                branch_col = None
                break

    start_col = _find_first_assessment_col(raw, range(0, max_row + 1), roll_col)
    data_start = _find_data_start_row(raw, max_row, roll_col)
    col_names = _build_column_names(raw, start_col=start_col)

    built = _build_assessment_table(
        raw,
        co_row=co_row,
        max_row=max_row,
        roll_col=roll_col,
        branch_col=branch_col,
        start_col=start_col,
        col_names=col_names,
        data_start=data_start,
    )
    if built is None:
        return source_path

    out_cols, _col_indices, rows, co_values, max_values, _assessment_cols = built
    df = _dataframe_from_assessment_table(out_cols, rows, co_values, max_values)
    return _write_workbook(df, source_path)


def _is_triple_header_layout(raw: pd.DataFrame) -> bool:
    if raw.shape[0] < 6 or raw.shape[1] < 8:
        return False
    roll_row = None
    for r in range(min(12, len(raw))):
        for c in range(min(6, raw.shape[1])):
            if _normalize_label(raw.iloc[r, c]) in ("roll no.", "roll no"):
                roll_row = r
                break
        if roll_row is not None:
            break
    if roll_row is None or roll_row < 3:
        return False
    if _find_max_marks_cell(raw, near_row=roll_row - 1) is None:
        return False
    co_row = roll_row - 2
    co_hits = 0
    for c in range(4, min(raw.shape[1], 30)):
        val = _cell_str(raw.iloc[co_row, c]).upper()
        if re.match(r"^CO\d+", val) or val in ("TOTAL", "TOTAL "):
            co_hits += 1
    return co_hits >= 3


def _from_triple_header_layout(raw: pd.DataFrame, source_path: str) -> str:
    roll_row = None
    roll_col = 1
    branch_col = 0
    for r in range(min(12, len(raw))):
        for c in range(min(6, raw.shape[1])):
            if _normalize_label(raw.iloc[r, c]) in ("roll no.", "roll no"):
                roll_row = r
                roll_col = c
                branch_col = c - 1 if c > 0 else 0
                break
        if roll_row is not None:
            break
    if roll_row is None:
        return source_path

    max_cell = _find_max_marks_cell(raw, near_row=roll_row - 1)
    if max_cell is None:
        return source_path
    max_row, _ = max_cell
    co_row = max_row - 1
    start_col = roll_col + 3
    data_start = roll_row + 1
    col_names = _build_column_names(raw, start_col=start_col)

    built = _build_assessment_table(
        raw,
        co_row=co_row,
        max_row=max_row,
        roll_col=roll_col,
        branch_col=branch_col,
        start_col=start_col,
        col_names=col_names,
        data_start=data_start,
    )
    if built is None:
        return source_path

    out_cols, _col_indices, rows, co_values, max_values, _assessment_cols = built
    df = _dataframe_from_assessment_table(out_cols, rows, co_values, max_values)
    return _write_workbook(df, source_path)


def _is_roll_index_layout(raw: pd.DataFrame) -> bool:
    if raw.shape[0] < 5 or raw.shape[1] < 3:
        return False
    for r in range(min(6, len(raw))):
        if _cell_str(raw.iloc[r, 0]).upper() == "CO":
            if r + 1 < len(raw) and _is_max_marks_label(raw.iloc[r + 1, 0]):
                return True
    return False


def _from_roll_index_layout(raw: pd.DataFrame, source_path: str) -> str:
    co_row = next(
        (r for r in range(min(6, len(raw))) if _cell_str(raw.iloc[r, 0]).upper() == "CO"),
        None,
    )
    if co_row is None:
        return source_path
    max_row = co_row + 1
    if max_row >= len(raw):
        return source_path

    start_col = 1
    col_names = _build_column_names(raw, start_col=start_col)
    built = _build_assessment_table(
        raw,
        co_row=co_row,
        max_row=max_row,
        roll_col=0,
        branch_col=None,
        start_col=start_col,
        col_names=col_names,
        data_start=max_row + 1,
    )
    if built is None:
        return source_path

    out_cols, _col_indices, rows, co_values, max_values, _assessment_cols = built
    df = _dataframe_from_assessment_table(out_cols, rows, co_values, max_values)
    return _write_workbook(df, source_path)


def _from_adc_layout(raw: pd.DataFrame, source_path: str) -> str:
    co_row = next(
        (r for r in range(min(8, len(raw))) if _cell_str(raw.iloc[r, 0]).upper() == "CO"),
        None,
    )
    if co_row is None:
        return source_path
    max_row = co_row + 1
    if max_row >= len(raw):
        return source_path

    first_assess_col = 3
    col_names = _build_column_names(raw, start_col=first_assess_col)
    col_indices = list(range(first_assess_col, raw.shape[1]))

    assessment_cols: list[str] = []
    assessment_indices: list[int] = []
    for name, j in zip(col_names, col_indices):
        if name.startswith("_skip_"):
            continue
        assessment_cols.append(name)
        assessment_indices.append(j)

    co_values = {n: _normalize_co_value(raw.iloc[co_row, j]) for n, j in zip(assessment_cols, assessment_indices)}
    max_key = _cell_str(raw.iloc[max_row, 0])
    max_values = {
        n: raw.iloc[max_row, j] for n, j in zip(assessment_cols, assessment_indices)
    }

    rows: list[tuple[str, dict]] = []
    for r in range(max_row + 1, len(raw)):
        roll = _cell_str(raw.iloc[r, 0])
        if not roll:
            continue
        branch = _cell_str(raw.iloc[r, 1])
        entry = {"Branch": branch}
        bonus_sum = 0.0
        has_bonus = False
        for name, j in zip(assessment_cols, assessment_indices):
            val = raw.iloc[r, j]
            if is_bonus_column(name):
                try:
                    bonus_sum += float(val)
                    has_bonus = True
                except (TypeError, ValueError):
                    pass
            else:
                entry[name] = val
        if has_bonus:
            entry["Bonus"] = bonus_sum
        rows.append((roll, entry))

    if not rows:
        return source_path

    out_cols = ["Branch"] + [c for c in assessment_cols if not is_bonus_column(c)]
    if any(is_bonus_column(c) for c in assessment_cols):
        out_cols.append("Bonus")
    for req in [c for c in assessment_cols if _is_trailer_column(c)]:
        if req not in out_cols and any(str(c).lower() == req.lower() for c in assessment_cols):
            out_cols.append(req)

    df = pd.DataFrame(index=["CO", "Max_Marks"] + [r for r, _ in rows], columns=out_cols)
    for name in out_cols:
        if name == "Branch":
            df.loc["CO", name] = ""
            df.loc["Max_Marks", name] = ""
            for roll, entry in rows:
                df.loc[roll, name] = entry.get("Branch", "")
        elif name == "Bonus":
            df.loc["CO", name] = ""
            df.loc["Max_Marks", name] = ""
            for roll, entry in rows:
                df.loc[roll, name] = entry.get("Bonus", 0)
        else:
            df.loc["CO", name] = co_values.get(name, "")
            df.loc["Max_Marks", name] = max_values.get(name, "")
            for roll, entry in rows:
                if name in entry:
                    df.loc[roll, name] = entry[name]

    max_index = "Max_Marks_scaled" if "scaled" in max_key.lower() else "Max_Marks"
    if max_index != "Max_Marks":
        df.rename(index={"Max_Marks": max_index}, inplace=True)

    return _write_workbook(df, source_path)


def _patch_standard_dataframe(df: pd.DataFrame) -> pd.DataFrame | None:
    changed = False
    df = _rename_metadata_index(df)
    index_labels = {str(i).strip().upper() for i in df.index}
    if "CO" not in index_labels and "CO TO BE ENTERED" not in index_labels:
        return None

    co_key = next(
        i for i in df.index if str(i).strip().upper() in ("CO", "CO TO BE ENTERED")
    )
    if str(co_key).strip().upper() == "CO TO BE ENTERED":
        df.rename(index={co_key: "CO"}, inplace=True)
        co_key = "CO"
        changed = True
    max_key = None
    for i in df.index:
        label = str(i).strip().upper()
        if label in ("MAX_MARKS", "MAX_MARKS_SCALED", "MAX MARKS", "MARKS"):
            max_key = i
            break
    if max_key is not None and str(max_key).strip().upper() in ("MARKS", "MAX MARKS"):
        df.rename(index={max_key: "Max_Marks"}, inplace=True)
        max_key = "Max_Marks"
        changed = True

    bonus_cols = [c for c in df.columns if is_bonus_column(str(c)) or is_bonus_assessment_column(str(c))]
    if bonus_cols:
        changed = True
        bonus_series = pd.Series(0.0, index=[i for i in df.index if str(i).strip().upper() not in _METADATA_INDEX])
        for col in bonus_cols:
            for idx in bonus_series.index:
                try:
                    bonus_series.loc[idx] += float(df.loc[idx, col])
                except (TypeError, ValueError):
                    pass
            if co_key is not None:
                df.loc[co_key, col] = ""
            if max_key is not None:
                df.loc[max_key, col] = ""
        if "Bonus" not in df.columns:
            df["Bonus"] = pd.NA
        for idx in bonus_series.index:
            df.loc[idx, "Bonus"] = bonus_series.loc[idx]
        df.loc[co_key, "Bonus"] = ""
        if max_key is not None:
            df.loc[max_key, "Bonus"] = ""
        df.drop(columns=bonus_cols, inplace=True)

    for col in df.columns:
        if str(col).strip().upper() in ("RESULT", "GRADE_POINT", "BONUS", "NUMERIC_GRADE_POINT"):
            continue
        val = df.loc[co_key, col]
        if isinstance(val, str) and val.strip().lower() in ("none", "null"):
            df.loc[co_key, col] = ""
            changed = True
        elif is_co_empty(val) and not is_bonus_column(str(col)):
            pass

    df = _finalize_standard_columns(df)
    unnamed_cols = [c for c in df.columns if str(c).startswith("Unnamed")]
    if unnamed_cols:
        df.drop(columns=unnamed_cols, inplace=True)
        changed = True

    return df if changed else None


def _is_standard_layout(df: pd.DataFrame) -> bool:
    labels = {str(i).strip().upper() for i in df.index}
    has_co = "CO" in labels or "CO TO BE ENTERED" in labels
    has_max = labels & {"MAX_MARKS", "MAX_MARKS_SCALED", "MAX MARKS", "MARKS"}
    return has_co and bool(has_max)


def cleanup_normalized_workbook(resolved_path: str, original_path: str) -> None:
    """Remove a temp normalized file when it is no longer needed."""
    if os.path.abspath(resolved_path) == os.path.abspath(original_path):
        return
    path = Path(resolved_path)
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


def resolve_marks_workbook(file_path: str) -> str:
    """
    Return path to a workbook legacy_engine can consume.
    May be the original path or a normalized temp file under storage/uploads.
    """
    path = str(Path(file_path).resolve())
    if not Path(path).exists():
        return path

    raw = pd.read_excel(path, header=None)
    if _is_triple_header_layout(raw):
        return _from_triple_header_layout(raw, path)
    if _is_roll_index_layout(raw):
        return _from_roll_index_layout(raw, path)
    if _is_sample_layout(raw):
        return _from_sample_layout(raw, path)
    if _is_adc_branch_grid(raw):
        return _from_adc_layout(raw, path)

    try:
        df = pd.read_excel(path, header=0, index_col=0)
        df.dropna(how="all", inplace=True)
    except Exception:
        return path

    if not _is_standard_layout(df):
        return path

    patched = _patch_standard_dataframe(df)
    if patched is not None:
        return _write_workbook(patched, path)

    touched = df.copy()
    touched = _rename_metadata_index(touched)
    touched = _finalize_standard_columns(touched)
    unnamed_cols = [c for c in touched.columns if str(c).startswith("Unnamed")]
    if unnamed_cols:
        touched.drop(columns=unnamed_cols, inplace=True)
    if not touched.equals(df):
        return _write_workbook(touched, path)
    return path
