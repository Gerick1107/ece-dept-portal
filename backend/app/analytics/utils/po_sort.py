"""Natural sort for PO1..PO12 then PSO1..PSO3."""

from __future__ import annotations

import re


def sort_po_pso_keys(keys: list[str]) -> list[str]:
    def sort_key(name: str) -> tuple[int, int, str]:
        m = re.match(r"^(PO|PSO)(\d+)$", str(name).strip(), re.IGNORECASE)
        if m:
            kind = 0 if m.group(1).upper() == "PO" else 1
            return (kind, int(m.group(2)), "")
        return (2, 0, str(name))

    return sorted(keys, key=sort_key)
