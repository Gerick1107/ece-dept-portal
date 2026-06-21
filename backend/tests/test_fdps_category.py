"""Tests for FDP program text filter (NPTEL / MOOC substring match)."""

from __future__ import annotations

from sqlalchemy import select

from app.fdps.models.entities import FacultyFdp
from app.fdps.services.fdp_service import _apply_program_filter


def test_apply_program_filter_nptel_and_mooc():
    stmt = select(FacultyFdp)
    nptel_sql = str(_apply_program_filter(stmt, "NPTEL").whereclause).upper()
    mooc_sql = str(_apply_program_filter(stmt, "MOOC").whereclause).upper()
    assert "NPTEL" in nptel_sql
    assert "MOOC" in mooc_sql or "MOOG" in mooc_sql
