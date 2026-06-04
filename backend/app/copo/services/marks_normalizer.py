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
_METADATA_INDEX = frozenset({"CO", "MAX_MARKS", "MAX_MARKS_SCALED", "ROLL NO.", "ROLL NO", "BRANCH"})


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
        if not base or base.lower() in ("roll no.", "roll no", "branch"):
            names.append(f"_skip_{j}")
            continue
        if base.lower() in ("result", "grade_point", "grade point"):
            label = "Result" if base.lower() == "result" else "Grade_Point"
            if label not in names:
                names.append(label)
            else:
                names.append(f"_skip_{j}")
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


def _from_sample_layout(raw: pd.DataFrame, source_path: str) -> str:
    co_row = _find_row_label(raw, "co to be entered", col=1) or _find_row_label(raw, "co", col=1)
    if co_row is None:
        for r in range(min(10, len(raw))):
            if "co" in _cell_str(raw.iloc[r, 1]).lower():
                co_row = r
                break
    if co_row is None:
        return source_path

    max_row = co_row + 1
    if max_row >= len(raw) or "max" not in _cell_str(raw.iloc[max_row, 1]).lower():
        max_row = co_row + 1

    data_start = max_row + 1
    col_names = _build_column_names(raw, start_col=2)

    assessment_cols: list[str] = []
    col_indices: list[int] = []
    for j, name in enumerate(col_names, start=2):
        if name.startswith("_skip_"):
            continue
        sub = _cell_str(raw.iloc[1, j]).lower() if len(raw) > 1 else ""
        if sub in ("result", "grade_point", "grade point"):
            col_label = "Result" if sub == "result" else "Grade_Point"
            assessment_cols.append(col_label)
            col_indices.append(j)
            continue
        assessment_cols.append(name)
        col_indices.append(j)

    regular_cols = [
        c for c in assessment_cols if not is_bonus_column(c) and not is_bonus_assessment_column(c)
    ]

    co_values: dict[str, str] = {}
    max_values: dict[str, float | str] = {}
    for name, j in zip(assessment_cols, col_indices):
        if name in ("Result", "Grade_Point"):
            co_values[name] = ""
            max_values[name] = ""
            continue
        co_values[name] = _normalize_co_value(raw.iloc[co_row, j])
        max_val = raw.iloc[max_row, j]
        max_values[name] = "" if is_co_empty(max_val) else max_val

    rows: list[tuple[str, dict]] = []
    for r in range(data_start, len(raw)):
        roll = _cell_str(raw.iloc[r, 1])
        if not roll or roll.lower() in ("roll no.", "roll no", "nan"):
            continue

        branch_path = _cell_str(raw.iloc[r, 0])
        entry: dict = {"Branch": branch_path if branch_path and branch_path.lower() != "nan" else ""}
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
        return source_path

    out_cols = ["Branch"] + regular_cols
    if any(is_bonus_column(c) or is_bonus_assessment_column(c) for c in assessment_cols):
        out_cols.append("Bonus")
    for req in ("Result", "Grade_Point"):
        if req in assessment_cols and req not in out_cols:
            out_cols.append(req)

    seen = set()
    out_cols_unique = []
    for c in out_cols:
        if c not in seen:
            seen.add(c)
            out_cols_unique.append(c)
    out_cols = out_cols_unique

    max_index = "Max_Marks"
    df = pd.DataFrame(index=["CO", max_index] + [r for r, _ in rows], columns=out_cols)
    for name in out_cols:
        if name == "Branch":
            df.loc["CO", name] = ""
            df.loc[max_index, name] = ""
            for roll, entry in rows:
                df.loc[roll, name] = entry.get("Branch", "")
        elif name == "Bonus":
            df.loc["CO", name] = ""
            df.loc[max_index, name] = ""
            for roll, entry in rows:
                df.loc[roll, name] = entry.get("Bonus", 0)
        elif name in co_values or name in ("Result", "Grade_Point"):
            df.loc["CO", name] = co_values.get(name, "")
            df.loc[max_index, name] = max_values.get(name, "")
            for roll, entry in rows:
                if name in entry:
                    df.loc[roll, name] = entry[name]

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
    for req in ("Result", "Grade_Point"):
        if req not in out_cols and any(c.lower() == req.lower() for c in assessment_cols):
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
    if "CO" not in [str(i).strip() for i in df.index]:
        return None

    co_key = next(i for i in df.index if str(i).strip().upper() == "CO")
    max_key = None
    for i in df.index:
        if str(i).strip().upper() in ("MAX_MARKS", "MAX_MARKS_SCALED"):
            max_key = i
            break

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

    return df if changed else None


def _is_standard_layout(df: pd.DataFrame) -> bool:
    labels = {str(i).strip().upper() for i in df.index}
    return "CO" in labels and ("MAX_MARKS" in labels or "MAX_MARKS_SCALED" in labels)


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
    return path
