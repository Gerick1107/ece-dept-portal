from __future__ import annotations

import re

_COURSE_CODE_TOKEN_RE = re.compile(r"^[A-Z]{2,4}\d{2,4}[A-Z0-9]*$", re.I)
_BARE_DEPT_TOKENS = {"CSE", "ECE", "EVE", "MTH", "ENG", "ENT", "M.TECH", "B.TECH"}


def collapse_repeated_dept_prefix(text: str) -> str:
    """ECE ECE564/CSE564 -> ECE564/CSE564"""
    raw = (text or "").strip()
    if not raw:
        return raw
    parts = re.split(r"([/,])", raw)
    out: list[str] = []
    for part in parts:
        if part in "/,":
            out.append(part)
            continue
        token = part.strip()
        if not token:
            continue
        upper = token.upper()
        m = re.match(r"^([A-Z]{2,4})\s+\1(\d.*)$", upper.replace(" ", " "))
        if m:
            token = f"{m.group(1)}{m.group(2)}"
        else:
            m2 = re.match(r"^([A-Z]{2,4})\s+([A-Z]{2,4}\d+.*)$", upper)
            if m2 and m2.group(1) == m2.group(2)[: len(m2.group(1))]:
                token = m2.group(2)
        out.append(token)
    return "".join(out)


def split_course_code_name(cell_code: str, cell_name: str = "") -> tuple[str, str]:
    """
    Parse allocation sheet cells: consume consecutive CODE/ tokens from code+name
    until a non-code token (course title) is reached.
    """
    combined = collapse_repeated_dept_prefix(f"{(cell_code or '').strip()} {(cell_name or '').strip()}").strip()
    if not combined:
        return "", ""

    segments = [s.strip() for s in re.split(r"[,/]", combined) if s.strip()]
    code_tokens: list[str] = []
    name_tokens: list[str] = []
    for seg in segments:
        norm = seg.upper().replace(" ", "").replace("-", "")
        if _COURSE_CODE_TOKEN_RE.match(norm) or (
            re.match(r"^[A-Z]{2,4}\d", norm) and norm not in _BARE_DEPT_TOKENS
        ):
            code_tokens.append(norm)
        elif not code_tokens:
            code_tokens.append(norm)
        else:
            name_tokens.append(seg)
    if not name_tokens and len(code_tokens) > 1:
        last = code_tokens.pop()
        if not _COURSE_CODE_TOKEN_RE.match(last):
            name_tokens.append(last)
        else:
            code_tokens.append(last)

    if not name_tokens:
        name = (cell_name or "").strip()
    else:
        name = " ".join(name_tokens).strip()

    code = "/".join(code_tokens) if code_tokens else collapse_repeated_dept_prefix(cell_code)
    return code, name


def tokenize_course_codes(course_code: str) -> set[str]:
    raw = collapse_repeated_dept_prefix(course_code or "")
    tokens: set[str] = set()
    for part in re.split(r"[,/]", raw):
        t = part.strip().upper().replace(" ", "").replace("-", "")
        if not t or t in _BARE_DEPT_TOKENS:
            continue
        if _COURSE_CODE_TOKEN_RE.match(t) or re.match(r"^[A-Z]{2,4}\d", t):
            tokens.add(t)
    return tokens


def merge_ug_pg(values: list[str]) -> str:
    vals = {v.strip().upper() for v in values if v}
    if "UG/PG" in vals or ("UG" in vals and "PG" in vals):
        return "UG/PG"
    if "PG" in vals:
        return "PG"
    if "UG" in vals:
        return "UG"
    return "UG/PG"


def merge_core_elective(values: list[str]) -> str:
    vals = {v.strip() for v in values if v}
    if "Core/Elective" in vals or ("Core" in vals and "Elective" in vals):
        return "Core/Elective"
    if "Core" in vals:
        return "Core"
    if "Elective" in vals:
        return "Elective"
    return "Elective"
