"""Persisted CO-PO run summaries for analysis after admin purge."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class CopoRunAnalyticsSnapshot(Base):
    __tablename__ = "copo_run_analytics_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    course_title: Mapped[str] = mapped_column(String(512), nullable=False)
    evaluation_type: Mapped[str] = mapped_column(String(32), nullable=False, default="standard")
    scope_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    semester_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    result_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    run_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    preserved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
