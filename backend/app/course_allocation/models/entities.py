from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class CourseAllocation(Base):
    __tablename__ = "course_allocations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    faculty_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    faculty_id: Mapped[int | None] = mapped_column(
        ForeignKey("faculty.id", ondelete="SET NULL"), nullable=True, index=True
    )
    semester: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    academic_year: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    course_code: Mapped[str] = mapped_column(String(256), nullable=False)
    course_name: Mapped[str] = mapped_column(Text, nullable=False)
    ug_pg: Mapped[str] = mapped_column(String(16), nullable=False)
    core_elective: Mapped[str] = mapped_column(String(32), nullable=False)
    is_first_year: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    first_year_course_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="historical")
    is_faculty_placeholder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    course_catalog_id: Mapped[int | None] = mapped_column(
        ForeignKey("course_catalog.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CourseCatalogEntry(Base):
    __tablename__ = "course_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_code: Mapped[str] = mapped_column(String(256), nullable=False, unique=True, index=True)
    course_name: Mapped[str] = mapped_column(Text, nullable=False)
    ug_pg: Mapped[str] = mapped_column(String(16), nullable=False)
    core_elective: Mapped[str] = mapped_column(String(32), nullable=False)
    is_first_year: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CourseCodeAlias(Base):
    __tablename__ = "course_code_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("course_catalog.id", ondelete="CASCADE"), nullable=False, index=True
    )
    variant_code: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    variant_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FacultyNameAlias(Base):
    __tablename__ = "faculty_name_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    variant_name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    canonical_name: Mapped[str] = mapped_column(String(200), nullable=False)
    faculty_id: Mapped[int | None] = mapped_column(
        ForeignKey("faculty.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
