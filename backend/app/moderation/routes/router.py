from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.database.models.user import User, UserRole
from app.database.session import get_db
from app.moderation.services.course_service import (
    course_to_dict,
    create_course,
    delete_course,
    get_course,
    list_courses,
    update_course,
)
from app.moderation.services.grade_summary_service import (
    create_grade_criterion,
    delete_grade_criterion,
    get_grade_criterion,
    list_grade_criteria,
    update_grade_criterion,
)
from app.moderation.services.question_paper_service import (
    create_paper,
    delete_paper,
    get_paper,
    list_distinct_years,
    list_papers_for_course,
    paper_to_dict,
)
from app.utils.storage_paths import resolve_storage_path

router = APIRouter(prefix="/moderation", tags=["moderation"])

MAX_PAPER_BYTES = 20 * 1024 * 1024


# --- Courses -------------------------------------------------------------

class CourseRequest(BaseModel):
    course_code: str = Field(min_length=1, max_length=50)
    course_name: str = Field(min_length=1, max_length=200)


@router.get("/courses")
def get_courses(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    query: str | None = None,
    faculty: str | None = None,
):
    rows = list_courses(db, query=query, faculty=faculty)
    return {"items": [course_to_dict(r) for r in rows]}


@router.get("/courses/{course_id}")
def get_course_detail(
    course_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    row = get_course(db, course_id)
    if not row:
        raise HTTPException(status_code=404, detail="Course not found")
    return course_to_dict(row)


@router.post("/courses", status_code=status.HTTP_201_CREATED)
def add_course(
    body: CourseRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.faculty, UserRole.hod))],
):
    try:
        row = create_course(db, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return course_to_dict(row)


@router.put("/courses/{course_id}")
def edit_course(
    course_id: int,
    body: CourseRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.faculty, UserRole.hod))],
):
    row = get_course(db, course_id)
    if not row:
        raise HTTPException(status_code=404, detail="Course not found")
    try:
        row = update_course(db, row, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return course_to_dict(row)


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_course(
    course_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    row = get_course(db, course_id)
    if not row:
        raise HTTPException(status_code=404, detail="Course not found")
    delete_course(db, row)


# --- Question papers (nested under a course) ------------------------------

@router.get("/courses/{course_id}/papers")
def get_course_papers(
    course_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    year: int | None = None,
    sort: Literal["asc", "desc"] = "desc",
):
    if not get_course(db, course_id):
        raise HTTPException(status_code=404, detail="Course not found")
    rows = list_papers_for_course(db, course_id, year=year, sort=sort)
    return {
        "items": [paper_to_dict(r) for r in rows],
        "years": list_distinct_years(db, course_id),
    }


@router.post("/courses/{course_id}/papers", status_code=status.HTTP_201_CREATED)
async def upload_course_paper(
    course_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.faculty, UserRole.hod))],
    faculty_name: str = Form(...),
    year: int = Form(...),
    semester: str = Form(...),
    file: UploadFile = File(...),
):
    if not get_course(db, course_id):
        raise HTTPException(status_code=404, detail="Course not found")
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    content = await file.read()
    if len(content) > MAX_PAPER_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 20 MB)")
    try:
        row = create_paper(
            db,
            course_id=course_id,
            faculty_name=faculty_name,
            year=year,
            semester=semester,
            filename=file.filename,
            content=content,
            uploaded_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return paper_to_dict(row)


@router.get("/papers/{paper_id}/download")
def download_paper(
    paper_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    row = get_paper(db, paper_id)
    if not row:
        raise HTTPException(status_code=404, detail="Question paper not found")
    path = resolve_storage_path(row.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")
    return FileResponse(path, media_type="application/pdf", filename=row.original_filename)


@router.delete("/papers/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_paper(
    paper_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    row = get_paper(db, paper_id)
    if not row:
        raise HTTPException(status_code=404, detail="Question paper not found")
    delete_paper(db, row)


# --- Grade summary ---------------------------------------------------------

class GradeCriterionResponse(BaseModel):
    id: int
    course_code: str
    semester: str
    grade_letter: str
    min_marks: float
    max_marks: float
    remarks: str | None

    @classmethod
    def from_row(cls, row) -> "GradeCriterionResponse":
        return cls(
            id=row.id, course_code=row.course_code, semester=row.semester,
            grade_letter=row.grade_letter, min_marks=row.min_marks,
            max_marks=row.max_marks, remarks=row.remarks,
        )


class GradeCriterionRequest(BaseModel):
    course_code: str = Field(min_length=1, max_length=50)
    semester: str = Field(min_length=1, max_length=32)
    grade_letter: str = Field(min_length=1, max_length=5)
    min_marks: float
    max_marks: float
    remarks: str | None = None


@router.get("/grade-summary")
def get_grade_summary(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    course_code: str | None = None,
    semester: str | None = None,
):
    items = list_grade_criteria(db, course_code=course_code, semester=semester)
    return {"items": [GradeCriterionResponse.from_row(r) for r in items]}


@router.post("/grade-summary", response_model=GradeCriterionResponse, status_code=status.HTTP_201_CREATED)
def add_grade_criterion(
    body: GradeCriterionRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.faculty, UserRole.hod))],
):
    try:
        row = create_grade_criterion(db, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return GradeCriterionResponse.from_row(row)


@router.put("/grade-summary/{criterion_id}", response_model=GradeCriterionResponse)
def edit_grade_criterion(
    criterion_id: int,
    body: GradeCriterionRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.faculty, UserRole.hod))],
):
    row = get_grade_criterion(db, criterion_id)
    if not row:
        raise HTTPException(status_code=404, detail="Grade criterion not found")
    try:
        row = update_grade_criterion(db, row, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return GradeCriterionResponse.from_row(row)


@router.delete("/grade-summary/{criterion_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_grade_criterion(
    criterion_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    row = get_grade_criterion(db, criterion_id)
    if not row:
        raise HTTPException(status_code=404, detail="Grade criterion not found")
    delete_grade_criterion(db, row)