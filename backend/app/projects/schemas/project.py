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


class ProjectStudentSchema(BaseModel):
    id: int | None = None
    student_name: str


class ProjectBase(BaseModel):
    project_title: str = Field(min_length=1, max_length=1024)
    project_type: str
    semester: str = Field(min_length=1, max_length=128)
    faculty_id: int
    co_guide: str | None = None
    status: str = "Pending"
    credit: str | None = None
    grade: str | None = None
    students: list[str] = Field(default_factory=list)


class ProjectCreate(ProjectBase):
    @field_validator("project_type", mode="before")
    @classmethod
    def validate_project_type(cls, v: str) -> str:
        from app.projects.services.project_service import _normalize_type

        return _normalize_type(str(v))


class ProjectUpdate(BaseModel):
    project_title: str | None = None
    project_type: str | None = None
    semester: str | None = None
    faculty_id: int | None = None
    co_guide: str | None = None
    status: str | None = None
    credit: str | None = None
    grade: str | None = None
    students: list[str] | None = None


class ProjectResponse(BaseModel):
    id: int
    project_title: str
    project_type: str
    semester: str
    faculty_id: int
    faculty_name: str
    co_guide: str | None
    status: str
    credit: str | None
    grade: str | None
    students: list[str]
    sdg_review_status: str
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
    total_rows: int = 0
    skipped_rows: int = 0
    sdg_queued: int = 0
    errors: list[str] = Field(default_factory=list)


class SdgEditRequest(BaseModel):
    sdg_numbers: list[int] = Field(default_factory=list)


class ProjectUploadResponse(BaseModel):
    id: int
    filename: str
    filepath: str
    uploaded_by: int | None
    uploaded_at: datetime | None
    record_count: int
