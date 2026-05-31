"""Gap-fill scrape: insert publications missing by source_hash (faculty 1–27, ASC)."""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.publications.services.gap_fill_service import run_gap_fill_all


def main() -> int:
    summary = run_gap_fill_all()
    print()
    print("=== GAP FILL COMPLETE ===")
    print(f"Total faculty processed: {summary.total_faculty_processed}")
    print(f"Total new publications inserted: {summary.total_new_publications}")
    if summary.failed_faculty:
        print(f"Faculty with failures: {summary.failed_faculty}")
    else:
        print("Faculty with failures: []")
    return 1 if summary.failed_faculty else 0


if __name__ == "__main__":
    sys.exit(main())
