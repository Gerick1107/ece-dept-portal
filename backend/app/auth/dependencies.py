from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.auth.service import get_user_by_email
from app.database.models.user import User, UserRole
from app.database.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = get_user_by_email(db, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    return user


def require_roles(*roles: UserRole):
    def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles and user.role != UserRole.admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return checker


@dataclass
class FacultyScope:
    """Describes what faculty-owned data the current request is allowed to see.

    - ``see_all`` is True for admins (no filtering — full department visibility).
    - Otherwise the request is restricted to a single faculty member, identified
      by ``faculty_id`` (FK filters) and/or ``faculty_name`` (name-string filters
      used by awards/FDPs/contributions/co-guide).
    - A non-admin whose account is not linked to a faculty record gets an empty
      scope (``faculty_id`` and ``faculty_name`` both None, ``see_all`` False),
      which callers must treat as "no rows".
    """

    see_all: bool
    faculty_id: int | None
    faculty_name: str | None

    @property
    def is_empty(self) -> bool:
        """True when a scoped (non-admin) user has no linked faculty → show nothing."""
        return not self.see_all and self.faculty_id is None


def get_faculty_scope(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> FacultyScope:
    """Resolve the per-faculty data scope for the current user.

    Admins see everything. Every other role is restricted to their own linked
    faculty record.
    """
    if user.role == UserRole.admin:
        return FacultyScope(see_all=True, faculty_id=None, faculty_name=None)

    faculty_name: str | None = None
    if user.faculty_id is not None:
        # Imported lazily to avoid a circular import at module load time.
        from app.publications.models.entities import Faculty

        faculty = db.get(Faculty, user.faculty_id)
        faculty_name = faculty.name if faculty else None
    return FacultyScope(see_all=False, faculty_id=user.faculty_id, faculty_name=faculty_name)


FacultyScopeDep = Annotated[FacultyScope, Depends(get_faculty_scope)]
