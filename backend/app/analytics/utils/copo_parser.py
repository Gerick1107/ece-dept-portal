"""Parse CO-PO ``result_summary`` JSON into chart-friendly structures."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_PO_KEYS = [f"PO{i}" for i in range(1, 13)] + ["PSO1", "PSO2", "PSO3"]


def _coerce_percent(value: Any) -> float | None:
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if num <= 1:
        num *= 100.0
    return round(num, 2)


def parse_copo_result_summary(result_summary: dict | None) -> dict | None:
    if not result_summary or not isinstance(result_summary, dict):
        return None

    intermediate = result_summary.get("intermediate")
    if not isinstance(intermediate, dict):
        intermediate = result_summary

    co_stats = intermediate.get("CO_stats") or {}
    pct_above = co_stats.get("pct_above") if isinstance(co_stats, dict) else {}
    co_attainment: dict[str, float] = {}
    if isinstance(pct_above, dict):
        for key, val in pct_above.items():
            parsed = _coerce_percent(val)
            if parsed is not None:
                co_attainment[str(key).strip()] = parsed

    po_raw = (
        intermediate.get("final_po_pso_attainment")
        or intermediate.get("po_pso_attainment")
        or intermediate.get("direct_po_pso_attainment")
        or {}
    )
    po_attainment: dict[str, float] = {}
    if isinstance(po_raw, dict):
        for key in _PO_KEYS:
            if key in po_raw:
                parsed = _coerce_percent(po_raw[key])
                if parsed is not None:
                    po_attainment[key] = parsed

    co_po_mapping = intermediate.get("CO_PO_mapping") or {}
    mapping: dict[str, dict[str, float]] = {}
    if isinstance(co_po_mapping, dict):
        for co, row in co_po_mapping.items():
            if not isinstance(row, dict):
                continue
            mapping[str(co)] = {
                str(po): float(row[po])
                for po in row
                if row[po] is not None and not (isinstance(row[po], float) and row[po] != row[po])
            }

    unique_cos = result_summary.get("unique_COs") or intermediate.get("unique_COs") or list(co_attainment.keys())
    if isinstance(unique_cos, list):
        unique_cos = sorted(
            [str(c) for c in unique_cos],
            key=lambda c: int(re.findall(r"\d+", c)[0]) if re.findall(r"\d+", c) else 0,
        )
    else:
        unique_cos = list(co_attainment.keys())

    if not co_attainment and not po_attainment:
        logger.warning("result_summary missing CO/PO attainment fields")
        return None

    return {
        "co_attainment": co_attainment,
        "po_attainment": po_attainment,
        "co_po_mapping": mapping,
        "unique_cos": unique_cos,
    }
