import secrets

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.security import hash_password, verify_password
from app.config import get_settings
from app.database.models.user import User, UserRole
from app.utils.email_service import (
    generate_temporary_password,
    send_faculty_welcome_email,
    send_password_reset_email,
)

settings = get_settings()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(
        select(User).where(
            User.email == email.lower(),
            User.profile_removed.is_(False),
        )
    )


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user or not user.is_active or user.profile_removed:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_user(
    db: Session,
    email: str,
    full_name: str,
    password: str,
    role: UserRole,
    *,
    must_change_password: bool | None = None,
    send_welcome_email: bool = False,
    faculty_id: int | None = None,
) -> tuple[User, bool]:
    if must_change_password is None:
        must_change_password = role == UserRole.faculty
    user = User(
        email=email.lower(),
        full_name=full_name,
        hashed_password=hash_password(password),
        role=role,
        must_change_password=must_change_password,
        faculty_id=faculty_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    email_sent = False
    if send_welcome_email and role in (UserRole.faculty, UserRole.hod):
        email_sent = send_faculty_welcome_email(
            user.email,
            user.full_name,
            password,
            settings.portal_frontend_url,
        )
    return user, email_sent


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.hashed_password):
        raise ValueError("Current password is incorrect")
    user.hashed_password = hash_password(new_password)
    user.must_change_password = False
    db.commit()
    db.refresh(user)


def bootstrap_admin_if_needed(db: Session) -> None:
    """Create bootstrap admin when missing (e.g. after DB import with no admin row)."""
    if get_user_by_email(db, settings.bootstrap_admin_email):
        return
    create_user(
        db,
        email=settings.bootstrap_admin_email,
        full_name="Portal Administrator",
        password=settings.bootstrap_admin_password,
        role=UserRole.admin,
        must_change_password=False,
        send_welcome_email=False,
    )


def _get_manageable_user(db: Session, user_id: int, actor: User) -> User:
    if user_id == actor.id:
        raise ValueError("You cannot modify your own account")

    target = db.get(User, user_id)
    if target is None or target.profile_removed:
        raise ValueError("User not found")
    return target


def _ensure_not_last_admin(db: Session, target: User) -> None:
    if target.role != UserRole.admin:
        return
    admin_count = (
        db.scalar(
            select(func.count()).select_from(User).where(
                User.role == UserRole.admin,
                User.profile_removed.is_(False),
            )
        )
        or 0
    )
    if admin_count <= 1:
        raise ValueError("Cannot modify the only admin account")


def deactivate_user_account(db: Session, user_id: int, actor: User) -> None:
    """Block login while keeping name and email on the account."""
    target = _get_manageable_user(db, user_id, actor)
    if not target.is_active:
        raise ValueError("User is already inactive")
    target.is_active = False
    db.commit()


def activate_user_account(db: Session, user_id: int, actor: User) -> None:
    """Re-enable login for a deactivated account."""
    target = _get_manageable_user(db, user_id, actor)
    if target.is_active:
        raise ValueError("User is already active")
    target.is_active = True
    db.commit()


def purge_user_profile(db: Session, user_id: int, actor: User) -> None:
    """Remove personal data and login access; keep CO-PO and other records linked by user id."""
    target = _get_manageable_user(db, user_id, actor)
    _ensure_not_last_admin(db, target)

    target.email = f"removed.{target.id}.{secrets.token_hex(8)}@portal.removed"
    target.full_name = "Removed user"
    target.hashed_password = hash_password(secrets.token_urlsafe(32))
    target.is_active = False
    target.must_change_password = True
    target.profile_removed = True
    db.commit()


def send_forgot_password_email(db: Session, email: str) -> bool:
    """Set a temporary password and email it to the user if account exists and is active."""
    user = get_user_by_email(db, email)
    if user is None or not user.is_active:
        return False

    temporary_password = generate_temporary_password()
    user.hashed_password = hash_password(temporary_password)
    user.must_change_password = True
    db.commit()

    return send_password_reset_email(
        to_email=user.email,
        full_name=user.full_name,
        temporary_password=temporary_password,
        portal_url=settings.portal_frontend_url,
    )
