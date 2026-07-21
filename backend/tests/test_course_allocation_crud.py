"""Unit tests for course allocation CRUD helpers and schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.course_allocation.schemas.allocation import AllocationCreateRequest, AllocationUpdateRequest
from app.course_allocation.services.semester_service import academic_year_for_semester


def test_allocation_create_schema_requires_core_fields():
    with pytest.raises(ValidationError):
        AllocationCreateRequest(
            semester="",
            course_code="ECE101",
            course_name="Intro",
        )


def test_allocation_create_schema_validates_enums():
    row = AllocationCreateRequest(
        faculty_id=1,
        semester="Monsoon 2026",
        course_code="ECE101",
        course_name="Intro",
        ug_pg="UG",
        core_elective="Core",
    )
    assert row.source == "manual"
    assert academic_year_for_semester(row.semester) == "2026-27"

    with pytest.raises(ValidationError):
        AllocationCreateRequest(
            semester="Monsoon 2026",
            course_code="ECE101",
            course_name="Intro",
            ug_pg="XYZ",
        )


def test_allocation_update_schema_clear_faculty():
    body = AllocationUpdateRequest(clear_faculty=True, faculty_id=None)
    dumped = body.model_dump(exclude_unset=True)
    assert dumped["clear_faculty"] is True
    assert dumped.get("faculty_id") is None
