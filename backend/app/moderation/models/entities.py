from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ModerationCourse(Base):
    __tablename__ = "moderation_courses"
    __table_args__ = (UniqueConstraint("course_code", name="uq_moderation_courses_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    course_name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    papers: Mapped[list["QuestionPaper"]] = relationship(
        "QuestionPaper", back_populates="course", cascade="all, delete-orphan"
    )


class QuestionPaper(Base):
    __tablename__ = "moderation_question_papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("moderation_courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    faculty_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    semester: Mapped[str] = mapped_column(String(16), nullable=False)  # "Winter" | "Monsoon"
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    uploaded_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    course: Mapped[ModerationCourse] = relationship("ModerationCourse", back_populates="papers")


class GradeCriterion(Base):
    __tablename__ = "moderation_grade_criteria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    semester: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    grade_letter: Mapped[str] = mapped_column(String(5), nullable=False)
    min_marks: Mapped[float] = mapped_column(Float, nullable=False)
    max_marks: Mapped[float] = mapped_column(Float, nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )