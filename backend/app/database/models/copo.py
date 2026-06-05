"""
CO-PO module persistence: metadata and archives; raw marks are removable after processing.

copo_result_archives rows are created only via POST /copo/runs/{id}/archive-and-clear-marks
(optional). Normal evaluations store excel_result_path on copo_evaluation_runs only.
See docs/STORAGE.md.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class UploadStatus(str, enum.Enum):
    uploaded = "uploaded"
    processed = "processed"
    cleared = "cleared"


class EvaluationStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    archived = "archived"


class CopoMarksUpload(Base):
    """End-of-semester consolidated marks file. Cleared after processing if requested."""

    __tablename__ = "copo_marks_uploads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    upload_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="final_consolidated"
    )
    course_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[UploadStatus] = mapped_column(
        Enum(UploadStatus), default=UploadStatus.uploaded, nullable=False
    )
    parse_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", backref="copo_uploads")


class CopoEvaluationRun(Base):
    """One attainment run: stores summary JSON, not raw student marks after cleanup."""

    __tablename__ = "copo_evaluation_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    marks_upload_id: Mapped[int | None] = mapped_column(
        ForeignKey("copo_marks_uploads.id"), nullable=True
    )
    course_title: Mapped[str] = mapped_column(String(512), nullable=False)
    mapping_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    evaluation_type: Mapped[str] = mapped_column(String(32), nullable=False, default="standard")
    status: Mapped[EvaluationStatus] = mapped_column(
        Enum(EvaluationStatus), default=EvaluationStatus.pending, nullable=False
    )
    target_value: Mapped[int] = mapped_column(Integer, default=50)
    scope_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    semester_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    result_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    comparison_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    excel_result_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    marks_cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", backref="copo_runs")
    marks_upload = relationship("CopoMarksUpload", backref="evaluation_runs")


class CopoResultArchive(Base):
    """Exported report snapshot retained after marks cleanup."""

    __tablename__ = "copo_result_archives"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    evaluation_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("copo_evaluation_runs.id"), nullable=True, index=True
    )
    archive_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    archive_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    evaluation_run = relationship("CopoEvaluationRun", backref="archives")
