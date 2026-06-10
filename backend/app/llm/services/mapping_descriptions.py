"""Load CO/PO outcome descriptions from the CO-PO mapping workbook."""

from __future__ import annotations

import logging
import re

import pandas as pd

from app.config import get_settings
from app.copo.services.mapping_service import SHEET_PREFERENCE, extract_cos_for_course

logger = logging.getLogger(__name__)

_PO_HEADER_RE = re.compile(r"^(PO\d+|PSO\d+)$", re.IGNORECASE)
_CO_NUM_RE = re.compile(r"^(CO\d+)", re.IGNORECASE)

# CO descriptions sourced from: data/assets/default_mapping.xlsx (course outcome mapping UG sheet, column A)
CO_DESCRIPTION_SOURCE = "data/assets/default_mapping.xlsx — Course outcome mapping UG sheet (column A)"

NBA_PO_DESCRIPTIONS: dict[str, str] = {
    "PO1": "PO1: Engineering Knowledge",
    "PO2": "PO2: Problem Analysis",
    "PO3": "PO3: Design/Development of Solutions",
    "PO4": "PO4: Conduct Investigations of Complex Problems",
    "PO5": "PO5: Modern Tool Usage",
    "PO6": "PO6: The Engineer and Society",
    "PO7": "PO7: Environment and Sustainability",
    "PO8": "PO8: Ethics",
    "PO9": "PO9: Individual and Team Work",
    "PO10": "PO10: Communication",
    "PO11": "PO11: Project Management and Finance",
    "PO12": "PO12: Life-long Learning",
}


def extract_po_descriptions(mapping_path: str | None = None) -> tuple[dict[str, str], str]:
    """PO/PSO number → description text from the mapping sheet header rows."""
    path = mapping_path or get_settings().resolved_mapping_path
    descriptions: dict[str, str] = {}
    source = f"{path} — mapping sheet header rows"
    try:
        xl = pd.ExcelFile(path)
        for sheet in SHEET_PREFERENCE:
            if sheet not in xl.sheet_names:
                continue
            df = pd.read_excel(path, sheet_name=sheet, header=None)
            if df.shape[0] < 2 or df.shape[1] < 4:
                continue
            label_row = df.iloc[1]
            desc_row = df.iloc[0]
            for col_idx in range(1, df.shape[1]):
                label = label_row.iloc[col_idx]
                if pd.isna(label):
                    continue
                label_str = str(label).strip().upper()
                if not _PO_HEADER_RE.match(label_str):
                    continue
                desc_raw = desc_row.iloc[col_idx]
                desc = str(desc_raw).strip() if pd.notna(desc_raw) else ""
                if desc and desc.lower() not in ("nan", "po1"):
                    descriptions[label_str] = f"{label_str}: {desc}"
                else:
                    descriptions[label_str] = NBA_PO_DESCRIPTIONS.get(label_str, label_str)
            if descriptions:
                break
    except Exception as exc:
        logger.warning("Could not read PO descriptions from mapping file: %s", exc)
        descriptions = dict(NBA_PO_DESCRIPTIONS)
        source = "NBA standard PO1–PO12 definitions (mapping file unavailable)"
    if not descriptions:
        descriptions = dict(NBA_PO_DESCRIPTIONS)
        source = "NBA standard PO1–PO12 definitions (not found in mapping file)"
    return descriptions, source


def extract_co_descriptions_for_course(
    course_title: str, mapping_path: str | None = None
) -> tuple[dict[str, str], bool, str | None]:
    """
    Return CO descriptions only when substantive text exists in the mapping sheet.
    Does not fabricate descriptions.
    """
    path = mapping_path or get_settings().resolved_mapping_path
    co_labels = extract_cos_for_course(path, course_title)
    result: dict[str, str] = {}
    for label in co_labels:
        normalized = label.strip()
        m = _CO_NUM_RE.match(normalized)
        if not m:
            continue
        key = m.group(1).upper()
        remainder = normalized[m.end() :].strip()
        remainder = re.sub(r"^[:.\-\s]+", "", remainder).strip()
        if remainder and remainder.lower() not in ("nan", "n/a"):
            result[key] = f"{key}: {remainder}"
    if result:
        return result, True, CO_DESCRIPTION_SOURCE
    # TODO: CO descriptions not found in codebase - add source when available
    return {}, False, None
