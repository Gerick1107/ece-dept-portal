"""Load CO/PO outcome descriptions from the CO-PO mapping workbook."""

from __future__ import annotations

import logging
import re

import pandas as pd

from app.config import get_settings
from app.copo.services.mapping_service import SHEET_PREFERENCE, extract_cos_for_course

logger = logging.getLogger(__name__)

_PO_HEADER_RE = re.compile(r"^(PO\d+|PSO\d+)$", re.IGNORECASE)


def extract_po_descriptions(mapping_path: str | None = None) -> dict[str, str]:
    """PO/PSO number → description text from the mapping sheet header rows."""
    path = mapping_path or get_settings().resolved_mapping_path
    descriptions: dict[str, str] = {}
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
                    descriptions[label_str] = label_str
            if descriptions:
                break
    except Exception as exc:
        logger.warning("Could not read PO descriptions from mapping file: %s", exc)
    return descriptions


def extract_co_descriptions_for_course(course_title: str, mapping_path: str | None = None) -> dict[str, str]:
    """CO label → description (falls back when course-specific text is unavailable)."""
    path = mapping_path or get_settings().resolved_mapping_path
    co_labels = extract_cos_for_course(path, course_title)
    result: dict[str, str] = {}
    for label in co_labels:
        normalized = label.strip().upper()
        m = re.match(r"^(CO\d+)", normalized, re.IGNORECASE)
        key = m.group(1).upper() if m else normalized
        result[key] = f"{key}: Description not available"
    return result
