from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.models.user import User
from app.database.session import get_db
from app.llm.schemas import (
    CourseComparison,
    GenerateInsightsRequest,
    GenerateInsightsResponse,
    InsightCourseOption,
)
from app.llm.services.groq_service import LlmError
from app.llm.services import insights_service

router = APIRouter(prefix="/llm-insights", tags=["llm-insights"])


def _envelope(data: dict) -> dict:
    return {"success": True, "data": data}


@router.get("/courses")
def list_courses(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    items = [InsightCourseOption.model_validate(c) for c in insights_service.list_insight_courses(db, user)]
    return _envelope({"items": [i.model_dump() for i in items]})


@router.get("/comparison")
def course_comparison(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    course_title: str = Query(..., min_length=1),
    current_semester: str | None = Query(None),
    current_section: str | None = Query(None),
    previous_semester: str | None = Query(None),
    previous_section: str | None = Query(None),
):
    try:
        data = insights_service.get_course_comparison(
            db,
            user,
            course_title,
            current_semester=current_semester,
            current_section=current_section or None,
            previous_semester=previous_semester,
            previous_section=previous_section,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _envelope(CourseComparison.model_validate(data).model_dump())


@router.get("/cached")
def cached_insights(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    course_title: str = Query(..., min_length=1),
    current_semester: str | None = Query(None),
    current_section: str | None = Query(None),
    previous_semester: str | None = Query(None),
    previous_section: str | None = Query(None),
):
    try:
        data = insights_service.get_cached_insights(
            db,
            user,
            course_title.strip(),
            current_semester=current_semester,
            current_section=current_section or None,
            previous_semester=previous_semester,
            previous_section=previous_section,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _envelope(GenerateInsightsResponse.model_validate(data).model_dump())


@router.post("/generate", response_model=dict)
async def generate_insights(
    body: GenerateInsightsRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    try:
        data = await insights_service.generate_insights(
            db,
            user,
            course_title=body.course_title.strip(),
            run_id=body.run_id.strip() if body.run_id else None,
            regenerate=body.regenerate,
            current_semester=body.current_semester,
            current_section=body.current_section,
            previous_semester=body.previous_semester,
            previous_section=body.previous_section,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LlmError as exc:
        status = exc.status_code or 502
        if "not configured" in str(exc).lower():
            status = 503
        raise HTTPException(status_code=status, detail=str(exc)) from exc

    return _envelope(GenerateInsightsResponse.model_validate(data).model_dump())
