from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class EceEveProject(Base):
    __tablename__ = "ece_eve_projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_title: Mapped[str] = mapped_column(String(1024), nullable=False)
    project_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    semesters: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    faculty_id: Mapped[int | None] = mapped_column(
        ForeignKey("faculty.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    guide_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    co_guide: Mapped[str | None] = mapped_column(String(255), nullable=True)
    course_code: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    course_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    admission_year: Mapped[str | None] = mapped_column(String(20), nullable=True)
    program_definition: Mapped[str | None] = mapped_column(String(200), nullable=True)
    program_specialization: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    student_roll_nos: Mapped[str] = mapped_column(Text, nullable=False, default="")
    student_names: Mapped[str] = mapped_column(Text, nullable=False, default="")
    credit: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    upload_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("project_uploads.id", ondelete="SET NULL"), nullable=True
    )
    source_project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    sdg_review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    faculty: Mapped["Faculty"] = relationship("Faculty", foreign_keys=[faculty_id], lazy="joined")


from app.publications.models.entities import Faculty  # noqa: E402, F401
