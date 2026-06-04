from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.courses.services.course_service import create_course, course_display_label, list_courses
from app.database.models.user import User, UserRole
from app.database.session import get_db

router = APIRouter(prefix="/courses", tags=["courses"])


class CourseResponse(BaseModel):
    id: int
    course_code: str
    course_name: str
    label: str

    model_config = {"from_attributes": True}


class CourseCreateRequest(BaseModel):
    course_code: str = Field(min_length=1, max_length=20)
    course_name: str = Field(min_length=1, max_length=200)


class CourseListResponse(BaseModel):
    courses: list[CourseResponse]


@router.get("", response_model=CourseListResponse)
def get_courses(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    rows = list_courses(db)
    return CourseListResponse(
        courses=[
            CourseResponse(
                id=c.id,
                course_code=c.course_code,
                course_name=c.course_name,
                label=course_display_label(c),
            )
            for c in rows
        ]
    )


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def add_course(
    body: CourseCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    try:
        course = create_course(db, body.course_code, body.course_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CourseResponse(
        id=course.id,
        course_code=course.course_code,
        course_name=course.course_name,
        label=course_display_label(course),
    )
