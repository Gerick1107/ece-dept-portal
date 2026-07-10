"""Create TEST faculty login accounts for every active faculty member.

For each active row in the ``faculty`` directory this creates a portal ``users``
row (role=faculty) linked via ``users.faculty_id`` so that per-faculty data
scoping works. Emails and passwords are throwaway test values — real ones will
be issued later.

Idempotent: existing accounts (matched by generated email or already-linked
faculty_id) are left untouched and reported as "exists".

Usage:
    python scripts/create_faculty_test_accounts.py [--dry-run]
"""
from __future__ import annotations

import argparse
import re
import secrets
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from app.auth.security import hash_password
from app.database.models.user import User, UserRole
from app.database.session import SessionLocal
from app.publications.models.entities import Faculty

_EMAIL_DOMAIN = "ecetest.iiitd.ac.in"
_PREFIX_RE = re.compile(r"^(dr|prof|professor|mr|mrs|ms)\.?\s+", re.IGNORECASE)


def _slug(name: str) -> str:
    cleaned = _PREFIX_RE.sub("", (name or "").strip())
    tokens = [re.sub(r"[^a-z0-9]", "", t.lower()) for t in cleaned.split()]
    tokens = [t for t in tokens if t]
    if not tokens:
        return "faculty"
    if len(tokens) == 1:
        return tokens[0]
    return f"{tokens[0]}.{tokens[-1]}"


def _unique_email(base_slug: str, taken: set[str], faculty_id: int) -> str:
    email = f"{base_slug}@{_EMAIL_DOMAIN}"
    if email not in taken:
        return email
    return f"{base_slug}.{faculty_id}@{_EMAIL_DOMAIN}"


def _password() -> str:
    # 12+ chars with an upper, symbol and hex digits — memorable prefix for testing.
    return f"Ece@{secrets.token_hex(4)}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create test faculty accounts.")
    parser.add_argument("--dry-run", action="store_true", help="Show accounts without saving.")
    args = parser.parse_args()

    db = SessionLocal()
    created: list[tuple[str, str, str]] = []
    existing: list[tuple[str, str]] = []
    try:
        faculty = list(
            db.scalars(select(Faculty).where(Faculty.is_active.is_(True)).order_by(Faculty.name.asc())).all()
        )
        taken_emails = {u.email for u in db.scalars(select(User)).all()}
        linked_faculty_ids = {
            u.faculty_id for u in db.scalars(select(User).where(User.faculty_id.is_not(None))).all()
        }

        for fac in faculty:
            if fac.id in linked_faculty_ids:
                linked = db.scalar(select(User).where(User.faculty_id == fac.id))
                existing.append((fac.name, linked.email if linked else "?"))
                continue

            email = _unique_email(_slug(fac.name), taken_emails, fac.id)
            if email in taken_emails:
                existing.append((fac.name, email))
                continue

            password = _password()
            taken_emails.add(email)
            created.append((fac.name, email, password))

            if not args.dry_run:
                db.add(
                    User(
                        email=email,
                        full_name=fac.name,
                        hashed_password=hash_password(password),
                        role=UserRole.faculty,
                        faculty_id=fac.id,
                        must_change_password=False,
                    )
                )
        if not args.dry_run:
            db.commit()
    finally:
        db.close()

    print("=== FACULTY TEST ACCOUNTS ===")
    print(f"Active faculty: {len(created) + len(existing)} | created: {len(created)} | already existed: {len(existing)}")
    print()
    print(f"{'FACULTY':32} {'EMAIL':40} PASSWORD")
    print("-" * 90)
    for name, email, pw in created:
        print(f"{name[:31]:32} {email:40} {pw}")
    for name, email in existing:
        print(f"{name[:31]:32} {email:40} (already exists — unchanged)")
    if args.dry_run:
        print("\n(dry run — nothing saved)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
