"""One-time backfill of publications columns from existing raw_metadata JSON."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pymysql
from dotenv import load_dotenv

from app.publications.utils.metadata_backfill import build_updates_from_metadata

BACKEND_ROOT = Path(__file__).resolve().parents[1]
BATCH_SIZE = 100


def _load_env() -> None:
    load_dotenv(BACKEND_ROOT / ".env")


def _db_connect() -> pymysql.connections.Connection:
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "ece_dept_portal"),
        autocommit=False,
        cursorclass=pymysql.cursors.DictCursor,
    )


def _run_verification(conn: pymysql.connections.Connection) -> None:
    queries = [
        "SELECT is_patent, COUNT(*) AS cnt FROM publications GROUP BY is_patent",
        "SELECT COUNT(*) AS cnt FROM publications WHERE title IS NULL OR title = ''",
        "SELECT COUNT(*) AS cnt FROM publications WHERE link IS NOT NULL",
        (
            "SELECT COUNT(*) AS cnt FROM publications "
            "WHERE journal IS NOT NULL AND is_patent = FALSE"
        ),
        (
            "SELECT COUNT(*) AS cnt FROM publications "
            "WHERE conference IS NOT NULL AND is_patent = FALSE"
        ),
        (
            "SELECT COUNT(*) AS cnt FROM publications "
            "WHERE patent_number IS NOT NULL AND is_patent = TRUE"
        ),
    ]
    print("\n--- Verification ---")
    with conn.cursor() as cur:
        for sql in queries:
            cur.execute(sql)
            rows = cur.fetchall()
            print(sql)
            for row in rows:
                print(row)
            print()


def main() -> int:
    _load_env()
    conn = _db_connect()

    pub_count = 0
    patent_count = 0
    failed = 0
    processed = 0

    with conn.cursor() as cur:
        cur.execute("SELECT id, raw_metadata FROM publications ORDER BY id")
        rows = cur.fetchall()

    total = len(rows)
    batch_updates: list[tuple[dict[str, Any], int]] = []

    def flush_batch() -> None:
        nonlocal batch_updates, failed
        if not batch_updates:
            return
        with conn.cursor() as cur:
            for updates, pub_id in batch_updates:
                try:
                    cols = ", ".join(f"{k} = %s" for k in updates)
                    values = list(updates.values()) + [pub_id]
                    cur.execute(f"UPDATE publications SET {cols} WHERE id = %s", values)
                except Exception as exc:
                    failed += 1
                    print(f"ERROR publication id={pub_id}: {exc}", file=sys.stderr)
        conn.commit()
        batch_updates = []

    for row in rows:
        pub_id = row["id"]
        raw = row.get("raw_metadata")
        try:
            if not raw:
                meta: dict[str, Any] = {}
            else:
                meta = json.loads(raw)
                if not isinstance(meta, dict):
                    raise ValueError("raw_metadata is not a JSON object")

            updates = build_updates_from_metadata(meta)
            batch_updates.append((updates, pub_id))
            processed += 1
            if updates.get("is_patent"):
                patent_count += 1
            else:
                pub_count += 1

            if len(batch_updates) >= BATCH_SIZE:
                flush_batch()
                if processed % 100 == 0 or processed == total:
                    if processed == 100:
                        print(
                            f"[{processed}/{total}] Processed {processed} rows "
                            f"({pub_count} publications, {patent_count} patents)..."
                        )
                    else:
                        print(f"[{processed}/{total}] Processed {processed} rows...")
        except Exception as exc:
            failed += 1
            print(f"ERROR publication id={pub_id}: {exc}", file=sys.stderr)

    flush_batch()

    print("\n=== BACKFILL COMPLETE ===")
    print(f"Total rows processed: {processed}")
    print(f"Publications: {pub_count}")
    print(f"Patents: {patent_count}")
    print(f"Rows failed: {failed} (see errors above)")

    _run_verification(conn)
    conn.close()
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
