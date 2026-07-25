from __future__ import annotations

from pydantic import BaseModel, field_validator


_COURSE_TYPES = {"Core", "Elective", "Core/Elective"}


def _optional_type(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned not in _COURSE_TYPES:
        raise ValueError(f"type must be one of {sorted(_COURSE_TYPES)} or empty")
    return cleaned


class AllocationCreateRequest(BaseModel):
    faculty_name: str = ""
    faculty_id: int | None = None
    semester: str
    academic_year: str | None = None
    course_code: str
    course_name: str
    ug_type: str | None = None
    pg_type: str | None = None
    registered_students: int | None = None
    course_catalog_id: int | None = None
    source: str = "manual"
    is_faculty_placeholder: bool | None = None
    clear_faculty: bool = False

    @field_validator("semester", "course_code", "course_name")
    @classmethod
    def _required_strip(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned

    @field_validator("ug_type", "pg_type")
    @classmethod
    def _type_fields(cls, value: str | None) -> str | None:
        return _optional_type(value)

    @field_validator("registered_students")
    @classmethod
    def _registered(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value < 0:
            raise ValueError("registered_students cannot be negative")
        return value


class AllocationUpdateRequest(BaseModel):
    faculty_name: str | None = None
    faculty_id: int | None = None
    semester: str | None = None
    academic_year: str | None = None
    course_code: str | None = None
    course_name: str | None = None
    ug_type: str | None = None
    pg_type: str | None = None
    registered_students: int | None = None
    clear_registered_students: bool = False
    course_catalog_id: int | None = None
    is_faculty_placeholder: bool | None = None
    clear_faculty: bool = False

    @field_validator("ug_type", "pg_type")
    @classmethod
    def _type_fields(cls, value: str | None) -> str | None:
        return _optional_type(value)

    @field_validator("registered_students")
    @classmethod
    def _registered(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value < 0:
            raise ValueError("registered_students cannot be negative")
        return value


class AllocationResponse(BaseModel):
    id: int
    faculty_name: str
    faculty_id: int | None = None
    semester: str
    academic_year: str
    course_code: str
    course_name: str
    ug_type: str | None = None
    pg_type: str | None = None
    registered_students: int | None = None
    source: str
    is_faculty_placeholder: bool
    course_catalog_id: int | None = None

    model_config = {"from_attributes": True}
