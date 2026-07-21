from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class SdgBrief(BaseModel):
    id: int
    sdg_number: int
    sdg_name: str
    is_confirmed: bool
    confidence_score: float | None = None

    model_config = {"from_attributes": True}


class ProjectBase(BaseModel):
    project_title: str = Field(min_length=1, max_length=1024)
    project_type: str
    semesters: str = Field(min_length=1)
    faculty_id: int
    guide_name: str | None = None
    co_guide: str | None = None
    course_code: str | None = None
    course_name: str | None = None
    admission_year: str | None = None
    program_definition: str | None = None
    program_specialization: str | None = None
    student_roll_nos: str = ""
    student_names: str = ""
    credit: float | None = None


class ProjectCreate(ProjectBase):
    @field_validator("project_type", mode="before")
    @classmethod
    def validate_project_type(cls, v: str) -> str:
        from app.projects.services.project_service import _normalize_type

        return _normalize_type(str(v))


class ProjectUpdate(BaseModel):
    project_title: str | None = None
    project_type: str | None = None
    semesters: str | None = None
    faculty_id: int | None = None
    guide_name: str | None = None
    co_guide: str | None = None
    course_code: str | None = None
    course_name: str | None = None
    admission_year: str | None = None
    program_definition: str | None = None
    program_specialization: str | None = None
    student_roll_nos: str | None = None
    student_names: str | None = None
    credit: float | None = None


class ProjectResponse(BaseModel):
    id: int
    project_title: str
    project_type: str
    semesters: str
    faculty_id: int
    faculty_name: str
    guide_name: str | None = None
    co_guide: str | None
    course_code: str | None
    course_name: str | None
    admission_year: str | None = None
    program_definition: str | None = None
    program_specialization: str | None = None
    student_roll_nos: str = ""
    student_names: str = ""
    credit: float | None
    students: list[str] = Field(default_factory=list)
    student_rolls: list[str] = Field(default_factory=list)
    sdg_review_status: str
    sdg_ever_accepted: bool = False
    suggested_sdgs: list[SdgBrief] = Field(default_factory=list)
    confirmed_sdgs: list[SdgBrief] = Field(default_factory=list)
    upload_batch_id: int | None
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    pagination: dict


class ImportSummary(BaseModel):
    upload_id: int
    imported: int
    merged: int = 0
    total_rows: int = 0
    skipped_rows: int = 0
    sdg_queued: int = 0
    errors: list[str] = Field(default_factory=list)


class SdgEditRequest(BaseModel):
    sdg_numbers: list[int] = Field(default_factory=list)


class BulkSdgAcceptRequest(BaseModel):
    faculty_id: int
    from_semester: str = Field(min_length=1)
    to_semester: str = Field(min_length=1)


class ProjectUploadResponse(BaseModel):
    id: int
    filename: str
    filepath: str
    uploaded_by: int | None
    uploaded_at: datetime | None
    record_count: int
