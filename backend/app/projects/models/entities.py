from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Sdg(Base):
    __tablename__ = "sdgs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sdg_number: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    sdg_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    project_links: Mapped[list["ProjectSdg"]] = relationship("ProjectSdg", back_populates="sdg")


class ProjectUpload(Base):
    __tablename__ = "project_uploads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    filepath: Mapped[str] = mapped_column(String(1024), nullable=False)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_title: Mapped[str] = mapped_column(String(1024), nullable=False)
    project_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    semesters: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id", ondelete="RESTRICT"), nullable=False, index=True)
    co_guide: Mapped[str | None] = mapped_column(String(255), nullable=True)
    course_code: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    course_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    admission_year: Mapped[str | None] = mapped_column(String(20), nullable=True)
    program_definition: Mapped[str | None] = mapped_column(String(200), nullable=True)
    program_specialization: Mapped[str | None] = mapped_column(String(200), nullable=True)
    student_roll_nos: Mapped[str] = mapped_column(Text, nullable=False, default="")
    student_names: Mapped[str] = mapped_column(Text, nullable=False, default="")
    credit: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    upload_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("project_uploads.id", ondelete="SET NULL"), nullable=True
    )
    sdg_review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    faculty: Mapped["Faculty"] = relationship("Faculty", foreign_keys=[faculty_id], lazy="joined")
    students: Mapped[list["ProjectStudent"]] = relationship(
        "ProjectStudent", back_populates="project", cascade="all, delete-orphan"
    )
    sdg_links: Mapped[list["ProjectSdg"]] = relationship(
        "ProjectSdg", back_populates="project", cascade="all, delete-orphan"
    )


class ProjectStudent(Base):
    __tablename__ = "project_students"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    student_name: Mapped[str] = mapped_column(String(255), nullable=False)

    project: Mapped[Project] = relationship("Project", back_populates="students")


class ProjectSdg(Base):
    __tablename__ = "project_sdgs"
    __table_args__ = (UniqueConstraint("project_id", "sdg_id", name="uq_project_sdgs_project_sdg"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    sdg_id: Mapped[int] = mapped_column(ForeignKey("sdgs.id", ondelete="CASCADE"), nullable=False, index=True)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped[Project] = relationship("Project", back_populates="sdg_links")
    sdg: Mapped[Sdg] = relationship("Sdg", back_populates="project_links")


from app.publications.models.entities import Faculty  # noqa: E402, F401
