"""Re-extract PDF text, re-chunk, and re-embed all meeting files.

Run inside the backend container after pulling RAG fixes:

  docker compose --env-file .env.docker exec backend \\
    python scripts/reindex_document_chunks.py

Optional:
  python scripts/reindex_document_chunks.py --type ece_faculty_meet
  python scripts/reindex_document_chunks.py --missing-embeddings-only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database.session import SessionLocal  # noqa: E402
from app.documents.services.ingestion_service import reindex_all_meeting_chunks  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Reindex meeting PDF chunks + embeddings")
    parser.add_argument(
        "--type",
        dest="document_type",
        default=None,
        help="Limit to one document type (e.g. ece_faculty_meet, senate)",
    )
    parser.add_argument(
        "--missing-embeddings-only",
        action="store_true",
        help="Only reindex files that have chunks without embeddings",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = reindex_all_meeting_chunks(
            db,
            document_type=args.document_type,
            missing_embeddings_only=args.missing_embeddings_only,
        )
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
