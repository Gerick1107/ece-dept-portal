"""Enrich publications with SerpAPI view_citation metadata (raw JSON in raw_metadata)."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pymysql
from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
STORAGE_DIR = BACKEND_ROOT / "storage"
KEY_USAGE_PATH = STORAGE_DIR / "key_usage.json"
CHECKPOINT_PATH = STORAGE_DIR / "enrichment_checkpoint.json"
SERPAPI_URL = "https://serpapi.com/search"
REQUEST_DELAY_SECONDS = 1.0
SEARCHES_PER_KEY_BUDGET = 250
TEST_MODE_LIMIT = 120


def _load_env() -> None:
    load_dotenv(BACKEND_ROOT / ".env")


def _db_connect() -> pymysql.connections.Connection:
    import os

    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "ece_dept_portal"),
        autocommit=False,
    )


def _load_api_keys() -> list[str]:
    import os

    raw = (os.getenv("SERP_API_KEYS") or "").strip()
    if not raw:
        single = (os.getenv("SERP_API_KEY") or "").strip()
        if single:
            return [single]
        return []
    return [k.strip() for k in raw.split(",") if k.strip()]


def _load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else default
    except (json.JSONDecodeError, OSError):
        return default


def _save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _init_key_usage(num_keys: int) -> dict[str, Any]:
    state = _load_json(KEY_USAGE_PATH, {})
    counts = state.get("counts")
    if not isinstance(counts, list) or len(counts) != num_keys:
        counts = [0] * num_keys
    idx = state.get("current_key_index", 0)
    if not isinstance(idx, int) or idx < 0 or idx >= num_keys:
        idx = 0
    return {"current_key_index": idx, "counts": counts}


def _save_key_usage(state: dict[str, Any]) -> None:
    _save_json(KEY_USAGE_PATH, state)


def _load_checkpoint() -> int:
    data = _load_json(CHECKPOINT_PATH, {})
    last_id = data.get("last_completed_id", 0)
    return int(last_id) if isinstance(last_id, int) else 0


def _save_checkpoint(publication_id: int) -> None:
    _save_json(CHECKPOINT_PATH, {"last_completed_id": publication_id})


def _extract_citation_for_view(scholar_url: str | None) -> str | None:
    if not scholar_url:
        return None
    parsed = urlparse(scholar_url)
    query = parse_qs(parsed.query)
    values = query.get("citation_for_view")
    if not values:
        return None
    value = values[0].strip()
    return value or None


def _fetch_citation(
    client: httpx.Client,
    citation_id: str,
    api_key: str,
) -> tuple[dict[str, Any] | None, int | None, str | None]:
    """Returns (citation_dict, http_status, error_message)."""
    # Google Scholar URLs use citation_for_view=...; SerpAPI expects citation_id=...
    params = {
        "engine": "google_scholar_author",
        "view_op": "view_citation",
        "citation_id": citation_id,
        "api_key": api_key,
    }
    try:
        response = client.get(SERPAPI_URL, params=params)
    except httpx.HTTPError as exc:
        return None, None, str(exc)

    status = response.status_code
    try:
        payload = response.json()
    except ValueError:
        return None, status, f"non-JSON response (HTTP {status})"

    if status in (401, 429):
        return None, status, payload.get("error") if isinstance(payload, dict) else response.text

    if status >= 400:
        err = payload.get("error") if isinstance(payload, dict) else response.text
        return None, status, f"HTTP {status}: {err}"

    if not isinstance(payload, dict):
        return None, status, "unexpected payload format"

    if payload.get("error"):
        return None, status, str(payload["error"])

    citation = payload.get("citation")
    if not isinstance(citation, dict):
        return None, status, "missing citation object in response"

    return citation, status, None


def _is_key_exhausted(status: int | None, err: str | None) -> bool:
    if status in (401, 429):
        return True
    if not err:
        return False
    lower = err.lower()
    return any(
        phrase in lower
        for phrase in (
            "quota",
            "limit exceeded",
            "run out",
            "insufficient",
            "invalid api key",
            "exceeded your",
            "too many requests",
        )
    )


def _rotate_key(key_state: dict[str, Any], num_keys: int, reason: str) -> bool:
    """Advance to next key. Returns False if no keys remain."""
    key_idx = key_state["current_key_index"]
    print(f"  Key {key_idx}: {reason} — rotating to next key...")
    key_state["current_key_index"] = key_idx + 1
    _save_key_usage(key_state)
    return key_state["current_key_index"] < num_keys


def _count_stats(conn: pymysql.connections.Connection) -> tuple[int, int, int]:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM publications")
    total = int(cur.fetchone()[0])
    cur.execute(
        "SELECT COUNT(*) FROM publications WHERE raw_metadata IS NOT NULL"
    )
    enriched = int(cur.fetchone()[0])
    remaining = total - enriched
    return total, enriched, remaining


def _fetch_publications(
    conn: pymysql.connections.Connection,
) -> list[tuple[int, str, str | None]]:
    """Rows to process: raw_metadata IS NULL only (never re-process enriched rows)."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, title, scholar_url
        FROM publications
        WHERE raw_metadata IS NULL
        ORDER BY id ASC
        """
    )
    return [(int(r[0]), str(r[1]), r[2]) for r in cur.fetchall()]


def _update_raw_metadata(
    conn: pymysql.connections.Connection,
    publication_id: int,
    raw_metadata: str,
) -> None:
    cur = conn.cursor()
    cur.execute(
        "UPDATE publications SET raw_metadata = %s WHERE id = %s",
        (raw_metadata, publication_id),
    )
    conn.commit()


def _truncate_title(title: str, max_len: int = 55) -> str:
    t = title.strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 3] + "..."


def _print_run_plan(
    total: int,
    enriched: int,
    remaining: int,
    num_keys: int,
    test_mode: bool,
    batch_size: int,
    last_completed_id: int,
    run_limit: int | None,
) -> None:
    if run_limit is not None:
        mode = f"LIMITED RUN: first {run_limit} remaining publications"
    elif test_mode:
        mode = f"TEST MODE: running first {TEST_MODE_LIMIT} only"
    else:
        mode = "FULL MODE: all remaining"
    if last_completed_id > 0:
        checkpoint_msg = f"resuming from id={last_completed_id}"
    else:
        checkpoint_msg = "starting fresh"
    budget = num_keys * SEARCHES_PER_KEY_BUDGET
    print(f"Total publications: {total}")
    print(f"Already enriched (raw_metadata not null): {enriched}")
    print(f"Remaining: {remaining}")
    print(f"Keys loaded: {num_keys} (estimated budget: {budget} searches)")
    print(mode)
    print(f"This run will process up to: {batch_size}")
    print(f"Checkpoint: {checkpoint_msg}")
    print()


def _prompt_confirm(
    total: int,
    enriched: int,
    remaining: int,
    num_keys: int,
    test_mode: bool,
    batch_size: int,
    last_completed_id: int,
    run_limit: int | None,
) -> bool:
    _print_run_plan(
        total, enriched, remaining, num_keys, test_mode, batch_size, last_completed_id, run_limit
    )
    answer = input("Proceed? (y/n): ").strip().lower()
    return answer == "y"


def run(test_mode: bool, limit: int | None = None, auto_confirm: bool = False) -> int:
    _load_env()
    api_keys = _load_api_keys()
    if not api_keys:
        print("ERROR: No API keys found. Set SERP_API_KEYS in backend/.env")
        return 1

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    key_state = _init_key_usage(len(api_keys))
    last_completed_id = _load_checkpoint()

    conn = _db_connect()
    try:
        total, enriched, remaining = _count_stats(conn)
        rows = _fetch_publications(conn)
        effective_limit = limit
        if effective_limit is None and test_mode:
            effective_limit = TEST_MODE_LIMIT
        if effective_limit is not None:
            rows = rows[:effective_limit]
        batch_size = len(rows)

        if auto_confirm:
            _print_run_plan(
                total,
                enriched,
                remaining,
                len(api_keys),
                test_mode,
                batch_size,
                last_completed_id,
                effective_limit,
            )
            print("Auto-confirmed (--yes). Starting...\n")
        elif not _prompt_confirm(
            total,
            enriched,
            remaining,
            len(api_keys),
            test_mode,
            batch_size,
            last_completed_id,
            effective_limit,
        ):
            print("Aborted.")
            return 0

        stats = {
            "processed": 0,
            "skipped_already_done": 0,
            "no_citation_for_view": 0,
            "failed": 0,
        }

        with httpx.Client(timeout=60.0) as client:
            for idx, (pub_id, title, scholar_url) in enumerate(rows, start=1):
                try:
                    citation_for_view = _extract_citation_for_view(scholar_url)

                    if not citation_for_view:
                        _update_raw_metadata(conn, pub_id, "{}")
                        _save_checkpoint(pub_id)
                        stats["no_citation_for_view"] += 1
                        stats["processed"] += 1
                        print(
                            f"[{idx}/{batch_size}] {_truncate_title(title)!r} "
                            f"-> no citation_for_view in URL [stored {{}}]"
                        )
                        time.sleep(REQUEST_DELAY_SECONDS)
                        continue

                    while True:
                        key_idx = key_state["current_key_index"]
                        if key_idx >= len(api_keys):
                            print("\nAll API keys exhausted.")
                            _print_summary(stats, key_state)
                            return 2

                        if key_state["counts"][key_idx] >= SEARCHES_PER_KEY_BUDGET:
                            if not _rotate_key(
                                key_state,
                                len(api_keys),
                                f"reached {SEARCHES_PER_KEY_BUDGET} searches",
                            ):
                                print("\nAll API keys exhausted.")
                                _print_summary(stats, key_state)
                                return 2
                            continue

                        api_key = api_keys[key_idx]
                        citation, http_status, err = _fetch_citation(
                            client, citation_for_view, api_key
                        )

                        if _is_key_exhausted(http_status, err):
                            if not _rotate_key(
                                key_state,
                                len(api_keys),
                                f"API error ({http_status}: {err})",
                            ):
                                print("\nAll API keys exhausted.")
                                _print_summary(stats, key_state)
                                return 2
                            continue

                        if citation is None:
                            stats["failed"] += 1
                            print(
                                f"[{idx}/{batch_size}] {_truncate_title(title)!r} "
                                f"-> FAILED: {err} [key {key_idx}, "
                                f"{key_state['counts'][key_idx]} uses]"
                            )
                            break

                        key_state["counts"][key_idx] += 1
                        _save_key_usage(key_state)

                        raw_json = json.dumps(citation, ensure_ascii=False)
                        _update_raw_metadata(conn, pub_id, raw_json)
                        _save_checkpoint(pub_id)
                        stats["processed"] += 1

                        field_names = sorted(citation.keys())
                        fields_str = ", ".join(field_names) if field_names else "(none)"
                        print(
                            f"[{idx}/{batch_size}] {_truncate_title(title)!r} "
                            f"-> fields: {fields_str} "
                            f"[key {key_idx}, {key_state['counts'][key_idx]} uses]"
                        )
                        break

                except Exception as exc:
                    stats["failed"] += 1
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    print(
                        f"[{idx}/{batch_size}] {_truncate_title(title)!r} "
                        f"-> ERROR: {exc}"
                    )

                time.sleep(REQUEST_DELAY_SECONDS)

        _print_summary(stats, key_state)
        return 0
    finally:
        conn.close()


def _print_summary(stats: dict[str, int], key_state: dict[str, Any]) -> None:
    usage_parts = [
        f"key_{i}={key_state['counts'][i]}" for i in range(len(key_state["counts"]))
    ]
    print()
    print("=== ENRICHMENT COMPLETE ===")
    print(f"Processed: {stats['processed']}")
    print(f"Skipped (already done): {stats['skipped_already_done']}")
    print(f"No citation_for_view found: {stats['no_citation_for_view']}")
    print(f"Failed: {stats['failed']}")
    print(f"Key usage: {', '.join(usage_parts)}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Enrich publications with SerpAPI view_citation metadata."
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help=f"Process only the first {TEST_MODE_LIMIT} remaining publications (by id ASC).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Process at most N remaining publications (by id ASC). Overrides --test cap when set.",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt.",
    )
    args = parser.parse_args()
    try:
        return run(test_mode=args.test, limit=args.limit, auto_confirm=args.yes)
    except KeyboardInterrupt:
        print("\nInterrupted. Progress saved via checkpoint.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
