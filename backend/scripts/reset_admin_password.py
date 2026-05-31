"""Reset bootstrap admin password to BOOTSTRAP_ADMIN_PASSWORD from .env."""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.auth.security import hash_password
from app.auth.service import create_user, get_user_by_email
from app.config import get_settings
from app.database.models.user import UserRole
from app.database.session import SessionLocal

get_settings.cache_clear()
settings = get_settings()


def main() -> int:
    db = SessionLocal()
    try:
        email = settings.bootstrap_admin_email.lower()
        user = get_user_by_email(db, email)
        if user is None:
            create_user(
                db,
                email=email,
                full_name="Portal Administrator",
                password=settings.bootstrap_admin_password,
                role=UserRole.admin,
                must_change_password=False,
                send_welcome_email=False,
            )
            print(f"Created admin user: {email}")
        else:
            user.hashed_password = hash_password(settings.bootstrap_admin_password)
            user.is_active = True
            user.must_change_password = False
            user.role = UserRole.admin
            db.commit()
            print(f"Reset password for admin: {email}")
        print(f"Login with password from BOOTSTRAP_ADMIN_PASSWORD in .env")
        return 0
    except Exception as exc:
        print(f"FAILED: {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
