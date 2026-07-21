from __future__ import annotations

from pydantic import BaseModel, field_validator


_UG_PG = {"UG", "PG", "UG/PG"}
_CORE_ELECTIVE = {"Core", "Elective", "Core/Elective"}


class AllocationCreateRequest(BaseModel):
    faculty_name: str = ""
    faculty_id: int | None = None
    semester: str
    academic_year: str | None = None
    course_code: str
    course_name: str
    ug_pg: str = "UG"
    core_elective: str = "Core"
    is_first_year: bool = False
    first_year_course_name: str | None = None
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

    @field_validator("ug_pg")
    @classmethod
    def _ug_pg(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if cleaned not in _UG_PG:
            raise ValueError(f"ug_pg must be one of {sorted(_UG_PG)}")
        return cleaned

    @field_validator("core_elective")
    @classmethod
    def _core_elective(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if cleaned not in _CORE_ELECTIVE:
            raise ValueError(f"core_elective must be one of {sorted(_CORE_ELECTIVE)}")
        return cleaned


class AllocationUpdateRequest(BaseModel):
    faculty_name: str | None = None
    faculty_id: int | None = None
    semester: str | None = None
    academic_year: str | None = None
    course_code: str | None = None
    course_name: str | None = None
    ug_pg: str | None = None
    core_elective: str | None = None
    is_first_year: bool | None = None
    first_year_course_name: str | None = None
    course_catalog_id: int | None = None
    is_faculty_placeholder: bool | None = None
    clear_faculty: bool = False

    @field_validator("ug_pg")
    @classmethod
    def _ug_pg(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if cleaned not in _UG_PG:
            raise ValueError(f"ug_pg must be one of {sorted(_UG_PG)}")
        return cleaned

    @field_validator("core_elective")
    @classmethod
    def _core_elective(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if cleaned not in _CORE_ELECTIVE:
            raise ValueError(f"core_elective must be one of {sorted(_CORE_ELECTIVE)}")
        return cleaned


class AllocationResponse(BaseModel):
    id: int
    faculty_name: str
    faculty_id: int | None = None
    semester: str
    academic_year: str
    course_code: str
    course_name: str
    ug_pg: str
    core_elective: str
    is_first_year: bool
    first_year_course_name: str | None = None
    source: str
    is_faculty_placeholder: bool
    course_catalog_id: int | None = None

    model_config = {"from_attributes": True}
