from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int


class FacultyBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    designation: str | None = None
    department: str | None = None
    scholar_id: str = Field(min_length=3, max_length=64)
    join_year: int
    leave_year: int | None = None
    photo_url: str | None = None
    profile_link: str | None = None


class FacultyCreate(FacultyBase):
    pass


class FacultyUpdate(BaseModel):
    name: str | None = None
    designation: str | None = None
    department: str | None = None
    join_year: int | None = None
    leave_year: int | None = None
    photo_url: str | None = None
    profile_link: str | None = None
    is_active: bool | None = None


class FacultyResponse(FacultyBase):
    id: int
    total_citations: int
    h_index: int
    i10_index: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    total_publications: int = 0

    model_config = {"from_attributes": True}


class FacultyListResponse(BaseModel):
    items: list[FacultyResponse]
    pagination: PaginationMeta


class PublicationBase(BaseModel):
    title: str = Field(min_length=1, max_length=1024)
    authors: str | None = None
    publication_year: int | None = None
    publisher: str | None = None
    citation_count: int = 0
    link: str | None = None
    publication_date: str | None = None
    pages: str | None = None
    conference: str | None = None
    journal: str | None = None
    book: str | None = None
    volume: str | None = None
    issue: str | None = None
    is_patent: bool = False
    inventors: str | None = None
    patent_office: str | None = None
    patent_number: str | None = None
    application_number: str | None = None
    scholar_url: str | None = None
    pdf_url: str | None = None
    is_iiitd_publication: bool = False


class PublicationCreate(PublicationBase):
    faculty_ids: list[int] = Field(default_factory=list)


class PublicationUpdate(BaseModel):
    title: str | None = None
    authors: str | None = None
    publication_year: int | None = None
    publisher: str | None = None
    citation_count: int | None = None
    link: str | None = None
    publication_date: str | None = None
    pages: str | None = None
    conference: str | None = None
    journal: str | None = None
    book: str | None = None
    volume: str | None = None
    issue: str | None = None
    is_patent: bool | None = None
    inventors: str | None = None
    patent_office: str | None = None
    patent_number: str | None = None
    application_number: str | None = None
    scholar_url: str | None = None
    pdf_url: str | None = None
    is_iiitd_publication: bool | None = None
    faculty_ids: list[int] | None = None


class PublicationResponse(PublicationBase):
    id: int
    source_hash: str
    created_at: datetime
    updated_at: datetime
    faculty_ids: list[int] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class PublicationListResponse(BaseModel):
    items: list[PublicationResponse]
    pagination: PaginationMeta


class CsvImportSummary(BaseModel):
    inserted: int
    updated: int
    skipped: int
    duplicate_rows: int
    errors: list[str] = Field(default_factory=list)


class ScrapeTriggerRequest(BaseModel):
    faculty_id: int | None = None
    force: bool = False


class ScrapeTriggerResponse(BaseModel):
    message: str
    queued_faculty_ids: list[int] = Field(default_factory=list)


class SyncAllResponse(BaseModel):
    status: str
    message: str


class BulkDeleteRequest(BaseModel):
    publication_ids: list[int] = Field(default_factory=list)


class DeletionResponse(BaseModel):
    deleted_count: int
    blocked_hashes_added: int
