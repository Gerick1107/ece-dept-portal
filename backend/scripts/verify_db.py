"""Verify DATABASE_URL from backend/.env can reach MySQL."""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import create_engine, text

from app.config import get_settings


def _parse_mysql_url(url: str) -> tuple[str, int, str, str, str]:
    parsed = urlparse(url)
    if parsed.scheme not in {"mysql", "mysql+pymysql"}:
        raise ValueError(f"Expected mysql+pymysql URL, got scheme={parsed.scheme!r}")
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 3306
    user = unquote(parsed.username or "")
    password = unquote(parsed.password or "")
    database = (parsed.path or "").lstrip("/")
    return host, port, user, password, database


def main() -> int:
    settings = get_settings()
    url = settings.database_url
    host, port, user, _, database = _parse_mysql_url(url)

    print(f"MySQL -> {user}@{host}:{port}/{database}")

    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            version = conn.execute(text("SELECT VERSION()")).scalar_one()
            tables = conn.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = :db"
                ),
                {"db": database},
            ).scalar_one()
            alembic = conn.execute(
                text(
                    "SELECT version_num FROM alembic_version LIMIT 1"
                )
            ).scalar_one_or_none()
    except Exception as exc:
        print(f"FAILED: {exc}")
        print()
        print("Checks:")
        print("  1. MySQL Server service is running (Services.msc, e.g. MySQL80 / MySQL94).")
        print("  2. Port is 3306 for Windows MySQL (3307 was Docker only).")
        print("  3. Run data/sql/local_mysql_bootstrap.sql in Workbench as root.")
        print("  4. Update backend/.env DATABASE_URL with your Workbench credentials.")
        return 1

    print(f"OK: MySQL {version}")
    print(f"    tables in {database}: {tables}")
    print(f"    alembic_version: {alembic or '(not migrated yet — run: alembic upgrade head)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
