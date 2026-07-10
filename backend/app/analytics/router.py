from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics.services.awards_service import get_awards_analytics
from app.analytics.services.copo_service import get_copo_analytics, get_copo_run_analytics
from app.analytics.services.projects_service import get_projects_analytics
from app.analytics.services.publications_service import get_publications_analytics
from app.auth.dependencies import FacultyScope, get_current_user, get_faculty_scope
from app.database.models.user import User
from app.database.session import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _envelope(data: dict) -> dict:
    return {"success": True, "data": data}


@router.get("/copo")
def analytics_copo(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    scope: Annotated[FacultyScope, Depends(get_faculty_scope)],
    course_title: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
):
    # Non-admins see CO-PO runs they created or runs for courses they taught.
    return _envelope(
        get_copo_analytics(
            db,
            course_title=course_title,
            from_date=from_date,
            to_date=to_date,
            user_id=None if scope.see_all else user.id,
            faculty_id=None if scope.see_all else scope.faculty_id,
            restrict=not scope.see_all,
        )
    )


@router.get("/copo/run/{public_id}")
def analytics_copo_run(
    public_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    scope: Annotated[FacultyScope, Depends(get_faculty_scope)],
):
    data = get_copo_run_analytics(
        db,
        public_id,
        user_id=None if scope.see_all else user.id,
        faculty_id=None if scope.see_all else scope.faculty_id,
        restrict=not scope.see_all,
    )
    return _envelope(data or {})


@router.get("/projects")
def analytics_projects(
    db: Annotated[Session, Depends(get_db)],
    scope: Annotated[FacultyScope, Depends(get_faculty_scope)],
    semester: str | None = Query(default=None, description="Comma-separated semester tags"),
    project_type: str | None = Query(default="all"),
    course_name: str | None = None,
    guide_id: int | None = None,
    specialization: str | None = None,
):
    semesters = [s.strip() for s in (semester or "").split(",") if s.strip()] or None
    # Non-admins only see analytics for projects they guide.
    if not scope.see_all:
        guide_id = scope.faculty_id if scope.faculty_id is not None else -1
    return _envelope(
        get_projects_analytics(
            db,
            semesters=semesters,
            project_type=project_type,
            course_name=course_name,
            faculty_id=guide_id,
            specialization=specialization,
        )
    )


@router.get("/awards")
def analytics_awards(
    db: Annotated[Session, Depends(get_db)],
    scope: Annotated[FacultyScope, Depends(get_faculty_scope)],
    faculty_name: str | None = Query(default=None, description="Comma-separated faculty names"),
    year: str | None = Query(default=None, description="Comma-separated academic years"),
    exact_year: str | None = Query(default=None, description="Comma-separated exact years"),
    category: str | None = Query(default=None, description="Comma-separated categories"),
):
    faculty_names = [s.strip() for s in (faculty_name or "").split(",") if s.strip()] or None
    # Non-admins only see analytics for their own awards.
    if not scope.see_all:
        faculty_names = [scope.faculty_name] if scope.faculty_name else ["\x00__none__"]
    years = [s.strip() for s in (year or "").split(",") if s.strip()] or None
    exact_years = [int(s) for s in (exact_year or "").split(",") if s.strip().isdigit()] or None
    categories = [s.strip() for s in (category or "").split(",") if s.strip()] or None
    return _envelope(
        get_awards_analytics(
            db,
            faculty_names=faculty_names,
            years=years,
            exact_years=exact_years,
            categories=categories,
        )
    )


@router.get("/publications")
def analytics_publications(
    db: Annotated[Session, Depends(get_db)],
    scope: Annotated[FacultyScope, Depends(get_faculty_scope)],
    year: int | None = None,
    pub_type: str | None = Query(default="all"),
    is_patent: bool | None = None,
):
    faculty_id = None
    if not scope.see_all:
        faculty_id = scope.faculty_id if scope.faculty_id is not None else -1
    return _envelope(
        get_publications_analytics(
            db, year=year, pub_type=pub_type, is_patent=is_patent, faculty_id=faculty_id
        )
    )
