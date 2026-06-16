from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    evaluation_run_id: Mapped[int] = mapped_column(
        ForeignKey("copo_evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    assessment_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id", ondelete="SET NULL"), nullable=True)
    semester: Mapped[str] = mapped_column(String(50), nullable=False)
    section_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    co_mappings: Mapped[list["AssessmentCoMapping"]] = relationship(
        "AssessmentCoMapping", back_populates="assessment", cascade="all, delete-orphan"
    )


class AssessmentCoMapping(Base):
    __tablename__ = "assessment_co_mapping"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    semester: Mapped[str] = mapped_column(String(50), nullable=False)
    co_label: Mapped[str] = mapped_column(String(50), nullable=False)
    question_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weightage: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    assessment: Mapped[Assessment] = relationship("Assessment", back_populates="co_mappings")
