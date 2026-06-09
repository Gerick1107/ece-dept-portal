from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class FacultyAward(Base):
    __tablename__ = "faculty_awards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    faculty_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    year: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    exact_year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    awarded_by: Mapped[str | None] = mapped_column(String(500), nullable=True)
    award: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
