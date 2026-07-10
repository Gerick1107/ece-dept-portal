"""Backfill exact publication dates for the existing backlog.

Reads publisher pages (citation_* meta tags) and Crossref — no SerpAPI quota is
used. Only upgrades rows to a more precise date; safe to re-run.

Usage:
    python scripts/backfill_publication_dates.py [--limit N] [--delay SECONDS]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.publications.services.date_backfill_service import backfill_publication_dates


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill exact publication dates (no SerpAPI).")
    parser.add_argument("--limit", type=int, default=None, help="Max publications to process.")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between requests (seconds).")
    args = parser.parse_args()

    summary = backfill_publication_dates(limit=args.limit, delay_seconds=args.delay)
    print()
    print("=== PUBLICATION DATE BACKFILL COMPLETE ===")
    print(f"Checked: {summary['checked']}")
    print(f"Updated: {summary['updated']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
