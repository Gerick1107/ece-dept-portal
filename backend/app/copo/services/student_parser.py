"""Student roll / programme / branch parsing — extracted from legacy Flask app."""

import re

import pandas as pd

from app.copo.services.marks_normalizer import cleanup_normalized_workbook, resolve_marks_workbook


def parse_student_rolls(file_path: str) -> dict:
    original_path = file_path
    file_path = resolve_marks_workbook(file_path)
    try:
        return _parse_student_rolls_from_workbook(file_path)
    finally:
        cleanup_normalized_workbook(file_path, original_path)


def _parse_student_rolls_from_workbook(file_path: str) -> dict:
    raw = pd.read_excel(file_path, header=None)

    branch_col_idx = None
    data_start_row = None
    for r in range(min(10, len(raw))):
        for c in range(min(5, raw.shape[1])):
            val = str(raw.iloc[r, c]).strip()
            if val.lower() == "branch":
                branch_col_idx = c
                data_start_row = r + 1
                break
        if branch_col_idx is not None:
            break

    roll_branch_map: dict[str, str] = {}
    if branch_col_idx is not None and data_start_row is not None:
        roll_col_idx = 0
        for r in range(data_start_row, len(raw)):
            roll = str(raw.iloc[r, roll_col_idx]).strip()
            branch_str = str(raw.iloc[r, branch_col_idx]).strip()
            branch_str = branch_str.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            if roll and roll.lower() not in ("nan", ""):
                roll_branch_map[roll] = branch_str

    df = pd.read_excel(file_path, header=0, index_col=0)
    df.dropna(how="all", inplace=True)
    df.index = df.index.map(lambda x: str(x).strip() if isinstance(x, str) else x)

    metadata_labels = {"CO", "Max_Marks", "Max_Marks_scaled", "Roll No.", "Roll No", "Branch"}

    if "Branch" in df.columns:
        for idx in df.index:
            label = str(idx).strip()
            if label in metadata_labels or pd.isna(idx):
                continue
            roll = str(idx).strip()
            branch_str = df.loc[idx, "Branch"]
            if pd.isna(branch_str):
                continue
            branch_str = str(branch_str).strip()
            if branch_str and branch_str.lower() != "nan":
                roll_branch_map[roll] = branch_str

    if "Max_Marks_scaled" in df.index and "Max_Marks" not in df.index:
        df.rename(index={"Max_Marks_scaled": "Max_Marks"}, inplace=True)

    cos: list[str] = []
    if "CO" in df.index:
        for val in df.loc["CO"]:
            if isinstance(val, str):
                for co in val.split(","):
                    co = co.strip()
                    if co and re.match(r"^CO\d+$", co) and co not in cos:
                        cos.append(co)
    cos.sort(key=lambda x: int(re.findall(r"\d+", x)[0]) if re.findall(r"\d+", x) else 0)

    all_rolls = [
        str(idx).strip()
        for idx in df.index
        if not pd.isna(idx) and str(idx).strip() not in metadata_labels
    ]

    programmes: dict = {}
    branches: dict = {}

    def _extract_branch_from_string(branch_str: str):
        if not branch_str or branch_str.lower() == "nan":
            return None, None
        parts = [p.strip() for p in branch_str.split("/")]
        prog = None
        branch = None
        for p in parts:
            pl = p.lower()
            if "btech" in pl or "b.tech" in pl:
                prog = "UG"
            elif "mtech" in pl or "m.tech" in pl:
                prog = "PG"
            elif "phd" in pl:
                prog = "PhD"
        for p in parts:
            if "-IIITD" in p:
                branch = p.replace("-IIITD", "").replace("/IIITD", "").strip()
                break
            elif p.upper().startswith("ECE") or p.upper().startswith("CSE") or p.upper().startswith("CS"):
                branch = p.strip()
                break
        return prog, branch

    for roll in all_rolls:
        roll_upper = roll.upper()
        prog = None
        branch = None
        if roll in roll_branch_map:
            prog, branch = _extract_branch_from_string(roll_branch_map[roll])
        if prog is None:
            if roll_upper.startswith("MT"):
                prog = "PG"
            elif roll_upper.startswith("PHD"):
                prog = "PhD"
            elif re.match(r"^\d{7}$", roll):
                prog = "UG"
            else:
                prog = "Other"

        programmes.setdefault(prog, {"count": 0, "rolls": []})
        programmes[prog]["count"] += 1
        programmes[prog]["rolls"].append(roll)

        if branch:
            branch_key = f"{prog}::{branch}"
            branches.setdefault(
                branch_key, {"count": 0, "rolls": [], "programme": prog, "branch": branch}
            )
            branches[branch_key]["count"] += 1
            branches[branch_key]["rolls"].append(roll)

    return {
        "cos": cos,
        "programmes": {k: v["count"] for k, v in programmes.items()},
        "branches": {
            k: {"count": v["count"], "programme": v["programme"], "branch": v["branch"]}
            for k, v in branches.items()
        },
        "total_students": len(all_rolls),
        "rolls_by_programme": {k: v["rolls"] for k, v in programmes.items()},
        "rolls_by_branch": {k: v["rolls"] for k, v in branches.items()},
    }


def build_included_rolls(
    course_path: str,
    selected_programmes: list[str],
    selected_branches: list[str],
) -> list[str] | None:
    if not selected_programmes and not selected_branches:
        return None
    try:
        parsed = parse_student_rolls(course_path)
        included_rolls: set[str] = set()
        has_branch_data = bool(parsed.get("rolls_by_branch"))

        for prog in selected_programmes:
            if has_branch_data and selected_branches:
                prog_branches = [
                    br
                    for br, info in parsed["branches"].items()
                    if info.get("programme") == prog and br in selected_branches
                ]
                if prog_branches:
                    for branch in prog_branches:
                        included_rolls.update(parsed["rolls_by_branch"].get(branch, []))
                else:
                    prog_has_any_branches = any(
                        info.get("programme") == prog for info in parsed["branches"].values()
                    )
                    if not prog_has_any_branches:
                        included_rolls.update(parsed["rolls_by_programme"].get(prog, []))
            else:
                included_rolls.update(parsed["rolls_by_programme"].get(prog, []))

        return list(included_rolls) if included_rolls else None
    except Exception:
        return None


def summarize_scope_selection(
    selected_programmes: list[str], selected_branches: list[str]
) -> str:
    if not selected_programmes and not selected_branches:
        return "Default scope (non-MT/PhD filtering from the core processor)"
    parts = []
    if selected_programmes:
        parts.append("Programmes: " + ", ".join(selected_programmes))
    if selected_branches:
        parts.append(
            "Branches: " + ", ".join(branch.split("::", 1)[-1] for branch in selected_branches)
        )
    return " | ".join(parts)
